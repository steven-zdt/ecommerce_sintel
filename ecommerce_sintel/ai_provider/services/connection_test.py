"""
ai_provider/services/connection_test.py -- Plan "AI Provider Runtime" FASE 11.

AIProviderConnectionTestService: unico punto de entrada para "Probar conexion"
-- delega en el adapter real del proveedor (services/providers/). Reemplaza
connection_probe.py::probe_provider() de la campaña previa (misma logica HTTP,
ahora organizada en adapters + codigos de error categorizados en vez de un
string libre).
"""
from ai_provider.models import AIProvider
from ai_provider.services.providers import get_adapter
from ai_provider.services.providers.base import ConnectionTestResult


class AIProviderConnectionTestService:
    @staticmethod
    def test(provider: AIProvider) -> ConnectionTestResult:
        return get_adapter(provider).test_connection()
