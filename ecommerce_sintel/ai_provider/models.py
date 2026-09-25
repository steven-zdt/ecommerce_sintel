"""
ai_provider/models.py

Dominio "AI Provider" -- plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES
PARA CHAT SUPPORT", FASE 1 (2026-08-13). Fuente oficial de configuracion operativa
del/los motor(es) LLM usados por el chatbot -- reemplaza progresivamente a
LOCAL_MODEL_CHAIN (ai_engine/config.py), que se mantiene como bootstrap/fallback/
emergencia mientras dure la migracion (regla explicita del plan maestro).

Separacion arquitectonica (regla explicita del plan maestro):
  AI ENGINE  = cerebro del chatbot (NUNCA importa estos modelos ni Postgres directo,
               lee esta configuracion solo via HTTP interno -- fase posterior)
  SUPPORT    = canal de conversacion
  DASHBOARD  = gestion administrativa (expone estos modelos via API admin)
  AI PROVIDER DOMAIN (esta app) = configuracion de proveedores y modelos
  FRONTEND   = interfaz de administracion (/panel/soporte)

`kind` usa exactamente el mismo vocabulario que ya entiende
`ai_engine/llm_factory.py::_build_model()` (ollama-nativo/openai-compatible/
anthropic) -- la tabla de tipos no se reinventa, se hace configurable.
"""
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from ecommerce.base_models import SintelBaseModel
from shared.fields import EncryptedTextField
from ai_provider.services.url_guard import UnsafeProviderURL, validate_provider_url

# Plan "AI Provider Runtime" (2026-08-13), FASE 2: limites razonables para timeout/
# reintentos -- evita que un admin configure un proveedor que cuelgue el chat
# indefinidamente o reintente en exceso. Rango amplio a proposito (Ollama local
# puede tardar mas que un proveedor cloud bajo carga).
TIMEOUT_MIN_SECONDS = 5
TIMEOUT_MAX_SECONDS = 300
MAX_RETRIES_LIMIT = 5


class AIProvider(SintelBaseModel):
    KIND_OLLAMA_NATIVE = 'ollama-nativo'
    KIND_OPENAI_COMPATIBLE = 'openai-compatible'
    KIND_ANTHROPIC = 'anthropic'
    KIND_CHOICES = [
        (KIND_OLLAMA_NATIVE, 'Ollama (nativo)'),
        (KIND_OPENAI_COMPATIBLE, 'OpenAI-compatible (LM Studio, vLLM, OpenAI, DeepSeek, ...)'),
        (KIND_ANTHROPIC, 'Anthropic (Claude)'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    base_url = models.CharField(
        max_length=500, blank=True,
        help_text=(
            'Requerido para ollama-nativo/openai-compatible (ej. '
            'http://host.docker.internal:11434 para Ollama en Windows, '
            'http://host.docker.internal:1234/v1 para LM Studio en Windows, '
            'http://sintel_ollama:11434 para Ollama en Docker). No aplica a anthropic.'
        ),
    )
    api_key = EncryptedTextField(blank=True, help_text='Cifrada en reposo. Vacia para motores locales.')
    is_active = models.BooleanField(default=True)
    # FASE 2 (plan actual): "is_default" es distinto de AIChannelConfig.primary_model --
    # marca el proveedor por defecto general (ej. para un canal nuevo sin config
    # explicita todavia), no el modelo activo de un canal especifico. Unico activo a
    # la vez -- ver AIProviderCommands.set_default().
    is_default = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    timeout = models.PositiveIntegerField(
        default=90, validators=[MinValueValidator(TIMEOUT_MIN_SECONDS), MaxValueValidator(TIMEOUT_MAX_SECONDS)],
        help_text=f'Segundos. Entre {TIMEOUT_MIN_SECONDS} y {TIMEOUT_MAX_SECONDS}.',
    )
    max_retries = models.PositiveIntegerField(default=1, validators=[MaxValueValidator(MAX_RETRIES_LIMIT)])
    metadata = models.JSONField(default=dict, blank=True)
    # PLAN_LLMDINAMICO F1: version propia del proveedor (historial/rollback por proveedor).
    config_version = models.PositiveIntegerField(default=1)

    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_ok = models.BooleanField(null=True, blank=True)
    last_test_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    last_test_error = models.TextField(blank=True)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_kind_display()})'

    def clean(self):
        if self.kind in (self.KIND_OLLAMA_NATIVE, self.KIND_OPENAI_COMPATIBLE):
            if not self.base_url:
                raise ValidationError({'base_url': 'Requerido para este tipo de proveedor.'})
            # Deliberadamente NO se usa django.core.validators.URLValidator: exige un
            # dominio con TLD y rechaza hostnames Docker de una sola etiqueta
            # (sintel_ollama, host.docker.internal a veces si por el punto, pero
            # sintel_ollama:11434 -- el caso real mas usado en este proyecto -- no).
            # Verificacion minima: esquema http/https + host presente.
            parsed = urlparse(self.base_url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValidationError({'base_url': 'URL invalida (debe ser http:// o https://<host>[:puerto]).'})
            # INCIDENTE 2026-09-25: localhost/127.0.0.1 dentro de Docker es el propio contenedor, nunca el equipo con LM Studio/Ollama; guardarlo
            # producia un proveedor que "nunca conecta". Se rechaza al guardar (AI_PROVIDER_ALLOW_LOOPBACK=true solo para Django fuera de Docker).
            if (parsed.hostname or '').lower() in ('localhost', '127.0.0.1', '::1', '0.0.0.0') and not getattr(settings, 'AI_PROVIDER_ALLOW_LOOPBACK', False):
                raise ValidationError({'base_url': (
                    'localhost/127.0.0.1 dentro de Docker es el propio contenedor, no tu equipo. Usa http://host.docker.internal:PUERTO '
                    '(LM Studio: 1234, Ollama: 11434) o el nombre del servicio Docker (p. ej. http://sintel_ollama:11434).')})
            # PLAN_LLMDINAMICO F3: guard SSRF (metadatos de nube, link-local, API de Docker, credenciales en la URL).
            try:
                validate_provider_url(self.base_url)
            except UnsafeProviderURL as exc:
                raise ValidationError({'base_url': str(exc)})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AIModel(SintelBaseModel):
    """Un modelo concreto disponible en un AIProvider (ej. 'llama3.1:8b', 'gpt-4o-mini').
    `model_id` es el identificador literal que el proveedor espera -- nunca se traduce."""

    provider = models.ForeignKey(AIProvider, related_name='models', on_delete=models.CASCADE)
    model_id = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    # FASE 3 (plan actual): "default" del PROVEEDOR (cual de sus modelos se preselecciona
    # en la UI) -- distinto de AIChannelConfig.primary_model (cual modelo usa el chat).
    is_default = models.BooleanField(default=False)
    discovered_automatically = models.BooleanField(
        default=False,
        help_text='True si se agrego via descubrimiento automatico (ej. GET /api/tags de Ollama).',
    )
    temperature = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text='Vacio = usa el default del proveedor/motor (0.1 hoy en llm_factory.py).',
    )
    max_tokens = models.PositiveIntegerField(null=True, blank=True, help_text='Vacio = default del motor.')
    context_window = models.PositiveIntegerField(
        null=True, blank=True, help_text='Informativo -- no se envia al proveedor, solo referencia para el admin.',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['provider__display_order', 'model_id']
        constraints = [
            models.UniqueConstraint(fields=['provider', 'model_id'], name='unique_model_per_provider'),
        ]

    def __str__(self):
        return self.display_name or self.model_id


class AIChannelConfig(SintelBaseModel):
    """Que modelo usa un canal (hoy solo 'support_chat', extensible a futuro) como
    primario -- mismo concepto que la 1ra entrada de LOCAL_MODEL_CHAIN, ahora editable
    en runtime desde /panel/soporte sin tocar .env ni reiniciar contenedores."""

    CHANNEL_SUPPORT_CHAT = 'support_chat'
    # FASE 1 (mision de simplificacion arquitectonica, 2026-09-14): reusa
    # AIProvider/AIModel/AIChannelConfig/AIChannelFallback tal cual -- un
    # proveedor de embeddings es exactamente lo mismo que un proveedor de chat
    # (base_url/api_key/kind), la unica diferencia es QUE modelo eligio el
    # canal. Evita crear un "AIEmbeddingProvider" paralelo que duplicaria este
    # modelo entero (ver AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md
    # seccion 11 del prompt original: "no duplicar contexto"). Consumido por
    # ai_knowledge.services.embedding_service.EmbeddingService.
    CHANNEL_EMBEDDINGS = 'embeddings'
    CHANNEL_CHOICES = [
        (CHANNEL_SUPPORT_CHAT, 'Chat de Soporte'),
        (CHANNEL_EMBEDDINGS, 'Embeddings (RAG)'),
    ]

    channel = models.CharField(max_length=50, choices=CHANNEL_CHOICES, unique=True)
    # FASE 4/18 (plan actual): "IA activa/inactiva" del canal -- distinto de
    # AIProvider.is_active (el proveedor puede estar activo pero el canal
    # deshabilitado, ej. para apagar el chatbot sin desactivar el proveedor que
    # tambien usa otro canal). Si enabled=False, get_dynamic_llm() debe tratarlo
    # igual que "cadena vacia" (cae a LOCAL_MODEL_CHAIN) -- FASE 19.
    enabled = models.BooleanField(default=True)
    # PLAN_LLMDINAMICO F1/F7: sube en cada cambio que afecte a este canal (primario, fallbacks, o edicion/activacion de un proveedor o
    # modelo). Viaja en el endpoint interno y en los logs del ADK para saber con que configuracion se atendio un turno.
    config_version = models.PositiveIntegerField(default=1)
    primary_model = models.ForeignKey(
        AIModel, related_name='primary_for_channels', on_delete=models.PROTECT, null=True, blank=True,
    )
    # Overrides a nivel de canal -- vacio = usa el valor de AIModel/AIProvider.
    temperature = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(2.0)])
    max_tokens = models.PositiveIntegerField(null=True, blank=True)
    timeout = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(TIMEOUT_MIN_SECONDS), MaxValueValidator(TIMEOUT_MAX_SECONDS)],
    )
    metadata = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True,
    )

    def __str__(self):
        return f'Config de {self.get_channel_display()}'


class AIChannelFallback(SintelBaseModel):
    """Un eslabon de la cadena de fallback ordenada de un AIChannelConfig -- equivalente
    a las entradas 2+ de LOCAL_MODEL_CHAIN (llm_factory.py::get_llm() las encadena con
    .with_fallbacks())."""

    channel_config = models.ForeignKey(AIChannelConfig, related_name='fallbacks', on_delete=models.CASCADE)
    model = models.ForeignKey(AIModel, related_name='fallback_for_channels', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['channel_config', 'order'], name='unique_fallback_order_per_channel'),
        ]

    def __str__(self):
        return f'{self.channel_config} fallback #{self.order}: {self.model}'


class AIConfigRevision(SintelBaseModel):
    """PLAN_LLMDINAMICO F1/F18 -- historial inmutable de cambios de configuracion, base del rollback.

    scope='channel': snapshot del canal (enabled, primario, cadena de fallback, overrides) -- `version` = AIChannelConfig.config_version.
    scope='provider': snapshot de los campos NO secretos de un AIProvider -- `version` propia por proveedor.
    NUNCA guarda api_key ni ningun secreto (solo `has_api_key`): un rollback de proveedor conserva la key actual."""

    SCOPE_CHANNEL = 'channel'
    SCOPE_PROVIDER = 'provider'
    SCOPE_CHOICES = [(SCOPE_CHANNEL, 'Canal'), (SCOPE_PROVIDER, 'Proveedor')]

    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    target_uuid = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=50, blank=True)
    version = models.PositiveIntegerField()
    action = models.CharField(max_length=60)
    snapshot = models.JSONField(default=dict)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ['-version', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['scope', 'target_uuid', 'version'], name='unique_revision_version_per_target'),
        ]

    def __str__(self):
        return f'{self.scope}:{self.target_uuid} v{self.version} ({self.action})'
