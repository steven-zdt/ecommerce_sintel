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

    def build_runtime_config(self, model) -> dict:
        """Dict con la forma que ai_engine/llm_factory.py::_build_model() ya entiende
        (name/kind/base_url/model/api_key_env/api_key_value) -- mismo contrato que
        ai_provider/api/internal_ai.py ya serializa para el endpoint interno."""
        return {
            'name': self.provider.name, 'kind': self.provider.kind, 'base_url': self.provider.base_url,
            'model': model.model_id, 'api_key_env': None, 'api_key_value': self.provider.api_key or None,
        }

    def get_provider_health(self) -> dict:
        """Opcional (FASE 7) -- por default delega a test_connection()."""
        return self.test_connection().as_dict()
