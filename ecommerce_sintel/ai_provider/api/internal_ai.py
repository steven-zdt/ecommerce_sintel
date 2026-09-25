"""
ai_provider/api/internal_ai.py

Endpoint interno para que AI Engine resuelva que proveedor/modelo usar en runtime
(plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES", FASE 2, 2026-08-13).

Distinto de los demas endpoints en ecommerce/internal_ai_urls.py: esos actuan EN
NOMBRE de un usuario especifico (forwardean su JWT, permission_classes=[IsAdminUser]/
[IsAuthenticatedActiveUser]). Este es config de INFRAESTRUCTURA del propio motor --
se consulta al arrancar y periodicamente, sin ningun turno de chat ni JWT de usuario
de por medio. Sigue el mismo modelo de aislamiento ya establecido y documentado en el
proyecto para /internal/* (ver users/api/internal.py): la frontera de seguridad real
es de RED (Docker interno + nginx bloquea /api/v1/internal/* en produccion,
nginx-common.conf), no permisos de Django -- por eso AllowAny explicito aqui, en vez
de forzar una identidad de usuario que no tiene sentido para una llamada de
infraestructura.

Esta vista SI devuelve `api_key` descifrada: AI Engine la necesita en texto plano
para construir el cliente LLM real (ChatOpenAI/ChatAnthropic, igual que hoy hace con
OPENAI_API_KEY/ANTHROPIC_API_KEY desde settings) -- Django descifra server-side y se
la entrega al unico consumidor interno sancionado, mismo nivel de confianza que ya
existia (la key vivia en texto plano en .env; ahora vive cifrada en Postgres y solo
se descifra para este consumidor interno). La regla del plan maestro de "nunca
exponer la API key" aplica al FRONTEND/navegador (ver FASE 3, esa vista jamas
serializa `api_key`, solo `has_api_key`) -- no a este endpoint interno.

Ruteado bajo /api/v1/internal/ai/ (ecommerce/internal_ai_urls.py).
"""
import hmac
import logging

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_provider.services.providers import get_adapter
from ai_provider.services.selectors import AIChannelConfigSelector


logger = logging.getLogger(__name__)
SERVICE_TOKEN_HEADER = 'X-AI-Service-Token'


def _service_token_ok(request) -> bool:
    """PLAN_LLMDINAMICO F3: token de servicio ADK -> Django (mismo AI_SERVICE_TOKEN de F2, con rotacion via *_PREVIOUS), en tiempo constante."""
    given = request.headers.get(SERVICE_TOKEN_HEADER, '')
    valid = [t for t in (getattr(settings, 'AI_SERVICE_TOKEN', ''), getattr(settings, 'AI_SERVICE_TOKEN_PREVIOUS', '')) if t]
    return bool(given) and any(hmac.compare_digest(given.encode(), t.encode()) for t in valid)


def _serialize_model(model) -> dict:
    """FASE 19: delega en BaseProviderAdapter.build_runtime_config() en vez de
    duplicar el mapeo modelo->dict aqui -- este ya es exactamente el shape que
    ai_engine/llm_factory.py::_build_model() espera (name/kind/base_url/model/
    api_key_env/api_key_value), asi que AI Engine puede usar la entrada tal cual,
    sin volver a traducirla (antes _fetch_dynamic_chain() desanidaba 'provider'
    a mano en cada entrada). `api_key_value` viene descifrada -- ver docstring
    del modulo (consumidor interno sancionado)."""
    return get_adapter(model.provider).build_runtime_config(model)


class AiProviderConfigView(APIView):
    """
    GET /api/v1/internal/ai/provider-config/?channel=support_chat
    -> {"channel": "...", "enabled": bool, "primary": {...} | None, "fallbacks": [...]}

    FASE 15/19 (plan "AI Provider Runtime", 2026-08-13): shape reescrito de un
    'chain' plano a primary/fallbacks explicitos -- RuntimeConfigResolver
    (ai_engine/llm_factory.py) necesita distinguir el modelo primario del resto sin
    inferirlo por posicion, y `enabled` explicito permite que el motor loguee
    "canal apagado a proposito" distinto de "canal sin configurar" aunque ambos
    caigan igual a LOCAL_MODEL_CHAIN. URL/nombre de vista sin cambios (unico
    consumidor real es este mismo proyecto, ver docstring de arriba) -- solo cambia
    el body.

    primary/fallbacks ya vienen resueltos y en orden, saltando proveedores/modelos
    inactivos o el canal si esta deshabilitado (AIChannelConfigSelector.
    get_resolved_chain) -- AI Engine no necesita conocer el modelo de datos, solo
    consumir la lista. primary=None y fallbacks=[] = "no hay config real -> el
    motor debe caer a LOCAL_MODEL_CHAIN" (bootstrap/emergencia, regla explicita del
    plan maestro).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if not _service_token_ok(request):
            # Este endpoint devuelve API keys descifradas: enforce -> 403 uniforme (no revela si falto o fue incorrecto).
            enforce = getattr(settings, 'AI_PROVIDER_CONFIG_TOKEN_REQUIRED', False)
            logger.warning('security_event=ai_provider_config_token_invalid mode=%s', 'enforce' if enforce else 'monitor')
            if enforce:
                return Response({'error': 'forbidden'}, status=403)
        channel = request.query_params.get('channel', 'support_chat')
        config = AIChannelConfigSelector.get_or_create_config(channel)
        chain = AIChannelConfigSelector.get_resolved_chain(channel)
        primary, *fallbacks = chain if chain else (None, )
        return Response({
            'channel': channel,
            'enabled': config.enabled,
            'config_version': config.config_version,
            'primary': _serialize_model(primary) if primary else None,
            'fallbacks': [_serialize_model(m) for m in fallbacks],
        })
