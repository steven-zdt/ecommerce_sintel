"""ai_provider/services/providers -- Plan "AI Provider Runtime" FASE 7-10."""
from ai_provider.models import AIProvider
from ai_provider.services.providers.anthropic import AnthropicAdapter
from ai_provider.services.providers.base import BaseProviderAdapter
from ai_provider.services.providers.ollama import OllamaAdapter
from ai_provider.services.providers.openai_compatible import OpenAICompatibleAdapter

_ADAPTERS = {
    AIProvider.KIND_OLLAMA_NATIVE: OllamaAdapter,
    AIProvider.KIND_OPENAI_COMPATIBLE: OpenAICompatibleAdapter,
    AIProvider.KIND_ANTHROPIC: AnthropicAdapter,
}


def get_adapter(provider: AIProvider) -> BaseProviderAdapter:
    adapter_cls = _ADAPTERS.get(provider.kind)
    if adapter_cls is None:
        raise ValueError(f'Sin adapter registrado para kind={provider.kind!r}')
    return adapter_cls(provider)
