"""
ai_provider/services/model_discovery.py -- Plan "AI Provider Runtime" FASE 12.

Reemplaza connection_probe.py::discover_provider_models() de la campaña previa.
Ollama: GET /api/tags. OpenAI-compatible: GET /v1/models. Anthropic: sin
descubrimiento dinamico (ver providers/anthropic.py) -- el admin agrega el
modelo manualmente (frontend ya maneja la lista vacia con gracia, FASE 5).
"""
from ai_provider.models import AIProvider
from ai_provider.services.providers import get_adapter


def discover_models(provider: AIProvider) -> list[dict]:
    return get_adapter(provider).list_models()
