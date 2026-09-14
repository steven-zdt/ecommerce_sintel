"""
ai_provider/services/runtime_cache.py

FASE 20 (plan "AI Provider Runtime", 2026-08-13): invalidacion instantanea del
cache de runtime que mantiene AI Engine (ai_engine/llm_factory.py::
RuntimeConfigResolver, FASE 19). Antes de esta fase, un cambio guardado desde
/panel/soporte tardaba hasta _DYNAMIC_CHAIN_CACHE_TTL_SECONDS (15s) en reflejarse
en /chat -- funcional, pero no es "hot reload sin esperar nada" (lo que pide la
demo de FASE 21).

Diseno: no se cachean las entradas resueltas (name/kind/base_url/model/api_key)
en Redis -- solo un contador de generacion por canal
(`ai_runtime:<channel>:gen`). Cada mutacion relevante en AIProviderCommands/
AIModelCommands/AIChannelConfigCommands incrementa el contador; RuntimeConfigResolver
lo lee en cada resolucion (barato, un GET) y si difiere del que tiene cacheado,
fuerza un refetch inmediato saltandose el TTL -- sin serializar objetos LLM ni
depender de que Redis siga vivo para funcionar (si Redis falla, ver
_get_runtime_generation() en llm_factory.py: se trata igual que "sin cambios",
el TTL de 15s sigue siendo la red de seguridad, tal como ya documentaba FASE 19).

Comparte la misma instancia/DB de Redis que ya usa el checkpointer de LangGraph
(CHECKPOINTER_REDIS_URL, default redis://redis:6379/2 -- ver ai_engine/
redis_checkpointer.py y ai_engine/config.py) con un prefijo de clave distinto
('ai_runtime:') para no colisionar con las claves 'ai:cp:*' del checkpointer.
No agrega una DB nueva que justificar ni una variable de entorno nueva: Django no
tiene CHECKPOINTER_REDIS_URL seteada en su propio entorno (esa env var esta
scopeada al servicio sintel_ai en docker-compose.yml), asi que aqui se lee con el
mismo nombre y el mismo default -- si ese valor cambia alguna vez en
docker-compose.yml, hay que actualizarlo en los dos lugares (no hay forma de
compartir una sola fuente de verdad entre dos `environment:` de servicios
distintos en compose sin YAML anchors, fuera de alcance de esta fase).
"""
import redis
from decouple import config as env

RUNTIME_CACHE_REDIS_URL = env('CHECKPOINTER_REDIS_URL', default='redis://redis:6379/2')


def _client() -> redis.Redis:
    return redis.Redis.from_url(RUNTIME_CACHE_REDIS_URL, decode_responses=True, socket_timeout=2)


def invalidate(channel: str) -> None:
    """Incrementa el contador de generacion del canal -- nunca lanza: si Redis esta
    caido, el peor caso es que AI Engine siga sirviendo con el TTL de 15s (FASE 19),
    no que una mutacion admin falle por un problema de cache."""
    try:
        _client().incr(f'ai_runtime:{channel}:gen')
    except redis.RedisError:
        pass
