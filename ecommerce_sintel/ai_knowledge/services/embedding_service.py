"""
ai_knowledge/services/embedding_service.py

EmbeddingService -- resuelve el proveedor de embeddings activo
(AIChannelConfig.CHANNEL_EMBEDDINGS, ver ai_provider/models.py) y calcula el
vector de un texto. Llamada HTTP directa al proveedor (mismo estilo que
ai_provider/services/providers/*.py, que ya hablan con Ollama/OpenAI-
compatible para test de conexion/descubrimiento) -- no reusa
ai_engine/embeddings_factory.py a proposito: ai_engine no debe importarse
desde Django, y esta clase corre del lado Django (regla "AI Engine nunca
importa Postgres directo", ver models.py).
"""
import logging

import requests

from ai_provider.models import AIChannelConfig, AIProvider
from ai_provider.services.selectors import AIChannelConfigSelector

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30


class EmbeddingProviderUnavailable(Exception):
    """No hay un modelo de embeddings configurado/activo, o el proveedor no respondio."""


def _embed_via_ollama(provider: AIProvider, model_id: str, text: str) -> list[float]:
    resp = requests.post(
        f'{provider.base_url.rstrip("/")}/api/embeddings',
        json={'model': model_id, 'prompt': text},
        timeout=_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get('embedding')
    if not embedding:
        raise EmbeddingProviderUnavailable(f'Ollama no devolvio "embedding" en la respuesta: {data}')
    return embedding


def _embed_via_openai_compatible(provider: AIProvider, model_id: str, text: str) -> list[float]:
    headers = {}
    if provider.api_key:
        headers['Authorization'] = f'Bearer {provider.api_key}'
    resp = requests.post(
        f'{provider.base_url.rstrip("/")}/embeddings',
        json={'model': model_id, 'input': text},
        headers=headers,
        timeout=_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data['data'][0]['embedding']
    except (KeyError, IndexError) as exc:
        raise EmbeddingProviderUnavailable(f'Respuesta OpenAI-compatible sin "data[0].embedding": {data}') from exc


# anthropic no ofrece API de embeddings -- si el canal 'embeddings' queda
# configurado con un AIProvider kind=anthropic, se trata como no soportado
# (no hay fallback silencioso: mejor fallar explicito que devolver un vector
# incorrecto).
_DISPATCH = {
    AIProvider.KIND_OLLAMA_NATIVE: _embed_via_ollama,
    AIProvider.KIND_OPENAI_COMPATIBLE: _embed_via_openai_compatible,
}


class EmbeddingService:
    @staticmethod
    def get_active_model():
        """Retorna el AIModel activo del canal 'embeddings', o None si no hay
        ninguno configurado todavia (estado esperado antes de que un admin
        configure el canal desde /panel/soporte)."""
        config = AIChannelConfigSelector.get_or_create_config(AIChannelConfig.CHANNEL_EMBEDDINGS)
        if not config.enabled or not config.primary_model or not config.primary_model.is_active:
            return None
        return config.primary_model

    @staticmethod
    def embed_text(text: str) -> tuple[list[float], str]:
        """Calcula el embedding de `text` con el modelo activo del canal
        'embeddings'. Retorna (vector, model_id) -- el model_id se persiste
        junto al vector (AIKnowledgeChunk.embedding_model) para poder
        detectar embeddings generados con un modelo distinto al activo.
        Lanza EmbeddingProviderUnavailable si no hay modelo configurado o el
        proveedor no responde -- nunca devuelve un vector vacio/falso."""
        model = EmbeddingService.get_active_model()
        if model is None:
            raise EmbeddingProviderUnavailable(
                'No hay un modelo de embeddings activo configurado '
                '(AIChannelConfig.CHANNEL_EMBEDDINGS) -- configurar uno desde /panel/soporte.'
            )
        provider = model.provider
        if not provider.is_active:
            raise EmbeddingProviderUnavailable(f'El proveedor "{provider.name}" del canal embeddings esta inactivo.')

        embed_fn = _DISPATCH.get(provider.kind)
        if embed_fn is None:
            raise EmbeddingProviderUnavailable(
                f'El proveedor "{provider.name}" (kind={provider.kind}) no soporta embeddings.'
            )
        try:
            vector = embed_fn(provider, model.model_id, text)
        except requests.RequestException as exc:
            logger.warning('[ai_knowledge] embed_text fallo: proveedor=%s modelo=%s error=%s', provider.name, model.model_id, exc)
            raise EmbeddingProviderUnavailable(f'Proveedor de embeddings inalcanzable: {exc}') from exc
        return vector, model.model_id
