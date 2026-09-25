"""
ai_provider/services/providers/base.py

Plan "AI Provider Runtime" FASE 7. Interfaz minima que cada adapter concreto
(ollama.py/openai_compatible.py/anthropic.py) debe implementar. Reemplaza la
logica antes plana en connection_probe.py (campana previa) con una jerarquia
formal -- no cambia el comportamiento observable de /chat (llm_factory.py sigue
consumiendo el mismo formato de "entry" dict), solo como se organiza el codigo
que prueba/descubre/valida proveedores.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


# FASE 11: codigos de error categorizados -- nunca un string libre sin clasificar.
ERROR_DNS = 'DNS'
ERROR_CONNECTION_REFUSED = 'CONNECTION_REFUSED'
ERROR_TIMEOUT = 'TIMEOUT'
ERROR_NETWORK_UNREACHABLE = 'NETWORK_UNREACHABLE'
ERROR_LOOPBACK_URL = 'LOOPBACK_URL'
ERROR_UNAUTHORIZED = 'UNAUTHORIZED'
ERROR_NOT_FOUND = 'NOT_FOUND'
ERROR_MODEL_NOT_FOUND = 'MODEL_NOT_FOUND'
ERROR_INVALID_RESPONSE = 'INVALID_RESPONSE'
ERROR_TOOL_CALLING_UNSUPPORTED = 'TOOL_CALLING_UNSUPPORTED'
ERROR_UNKNOWN = 'UNKNOWN'
SUCCESS = 'SUCCESS'


@dataclass
class ConnectionTestResult:
    """Forma exacta pedida por FASE 11 -- nunca incluye api_key/token/secreto."""
    success: bool
    provider: str
    base_url: str
    model: str | None
    latency_ms: int | None
    http_status: int | None
    error_code: str
    error_message_safe: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return {
            'success': self.success, 'provider': self.provider, 'base_url': self.base_url,
            'model': self.model, 'latency_ms': self.latency_ms, 'http_status': self.http_status,
            'error_code': self.error_code, 'error_message_safe': self.error_message_safe,
            'timestamp': self.timestamp,
        }


_LOOPBACK_HOSTS = frozenset({'localhost', '127.0.0.1', '::1', '0.0.0.0'})

_MESSAGES = {
    ERROR_DNS: 'El nombre de host no se resuelve desde el servidor. Revisa la URL; en Docker usa host.docker.internal (tu equipo) '
               'o el nombre del servicio (p. ej. sintel_ollama).',
    ERROR_CONNECTION_REFUSED: 'Conexion rechazada: no hay ningun servicio escuchando en ese host y puerto. Si es LM Studio u Ollama en tu '
                              'equipo, inicia el servidor local y usa http://host.docker.internal:PUERTO.',
    ERROR_NETWORK_UNREACHABLE: 'No hay ruta hasta ese host desde el servidor (servicio apagado, puerto cerrado o firewall). Con LM Studio '
                               'verifica que el servidor local este iniciado y accesible desde otros equipos/contenedores.',
    ERROR_UNKNOWN: 'No se pudo establecer conexion (motivo no identificado). Revisa la URL, el puerto y que el servicio este iniciado.',
}


def is_loopback_url(base_url: str) -> bool:
    from urllib.parse import urlparse
    return (urlparse(base_url or '').hostname or '').lower() in _LOOPBACK_HOSTS


def connection_failure(base_url: str, code: str) -> tuple[str, str]:
    """(codigo, mensaje seguro en espanol) para un fallo de conexion. Si la URL apunta a localhost/127.0.0.1, la causa mas probable
    es que ese 'localhost' es el del CONTENEDOR (no tu equipo): se avisa explicitamente. Nunca incluye secretos."""
    message = _MESSAGES.get(code, _MESSAGES[ERROR_UNKNOWN])
    if is_loopback_url(base_url):
        return ERROR_LOOPBACK_URL, ('La URL usa localhost/127.0.0.1, que dentro de Docker es el propio contenedor y no tu equipo. '
                                    'Usa http://host.docker.internal:PUERTO (LM Studio suele ser el 1234, Ollama el 11434).')
    return code, message


class BaseProviderAdapter(ABC):
    """Un adapter se construye con el AIProvider real (nunca con credenciales sueltas)
    -- lee `base_url`/`api_key`/`timeout` directo del modelo."""

    def __init__(self, provider):
        self.provider = provider

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Ping real de disponibilidad -- NUNCA una generacion completa (costo/latencia).
        Debe categorizar el error con uno de los codigos de este modulo."""
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> list[dict]:
        """[{'model_id':..., 'display_name':...}, ...] -- [] si el proveedor no soporta
        descubrimiento dinamico (nunca lanza)."""
        raise NotImplementedError

    def validate_model(self, model_id: str) -> bool:
        """Default: busca `model_id` en list_models(). Un adapter puede sobreescribir
        con una llamada dedicada mas barata si el proveedor la ofrece."""
        return any(m['model_id'] == model_id for m in self.list_models())

    # ---- PLAN_LLMDINAMICO sec. 3/10: auth, TLS, timeouts y capacidades compartidos por todos los adapters ----
    CAPABILITY_KEYS = ('tool_calling', 'streaming', 'structured_output', 'vision', 'reasoning', 'json_mode')

    @classmethod
    def _empty_capabilities(cls) -> dict:
        """Todo "desconocido" (None): una capacidad solo pasa a True/False cuando el proveedor la declara de verdad."""
        return {key: None for key in cls.CAPABILITY_KEYS}

    def detect_capabilities(self, model_id: str) -> dict:
        """Capacidades declaradas por el proveedor para `model_id` (True/False/None). Default: todo desconocido. Nunca lanza."""
        return self._empty_capabilities()

    def _auth_headers(self) -> dict:
        key = self.provider.api_key
        auth_type = getattr(self.provider, 'auth_type', 'bearer')
        if not key or auth_type == 'none':
            return {}
        if auth_type == 'header':
            return {(self.provider.api_key_header or 'x-api-key'): key}
        return {'Authorization': f'Bearer {key}'}

    def _request_kwargs(self) -> dict:
        """timeout=(conexion, total), TLS y sin redirects (SSRF): mismos parametros en toda llamada HTTP del adapter."""
        return {
            'timeout': (getattr(self.provider, 'connect_timeout', 5) or 5, 10),
            'verify': getattr(self.provider, 'verify_tls', True),
            'allow_redirects': False,
        }

    def build_runtime_config(self, model) -> dict:
        """Dict con la forma que consume el ADK (provider_registry.py) y ai_engine/llm_factory.py:
        name/kind/base_url/model/api_key_env/api_key_value + (PLAN_LLMDINAMICO) provider_uuid, auth_type, api_key_header, verify_tls y
        `generation` (temperature/top_p/max_tokens; el llamador puede aplicar overrides del canal). Mismo contrato que
        ai_provider/api/internal_ai.py serializa para el endpoint interno."""
        return {
            'name': self.provider.name, 'kind': self.provider.kind, 'base_url': self.provider.base_url,
            'model': model.model_id, 'api_key_env': None, 'api_key_value': self.provider.api_key or None,
            'provider_uuid': str(self.provider.uuid),
            'auth_type': getattr(self.provider, 'auth_type', 'bearer'),
            'api_key_header': getattr(self.provider, 'api_key_header', '') or None,
            'verify_tls': getattr(self.provider, 'verify_tls', True),
            'generation': {'temperature': model.temperature, 'top_p': model.top_p, 'max_tokens': model.max_tokens},
        }

    def get_provider_health(self) -> dict:
        """Opcional (FASE 7) -- por default delega a test_connection()."""
        return self.test_connection().as_dict()
