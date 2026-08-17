"""
Suite minima de tests unitarios del Support Agent (Bloque 10 del plan de
separacion Support vs Engineering, 2026-08-08). Cierra el hueco mas grande
encontrado en esa fase: ai_engine no tenia NINGUN test unitario en Python
-- toda la cobertura de IA vivia mockeada del lado Django (support/tests.py).

No pretende cubrir el checklist completo de Bloque 10 (unit/integracion/E2E/
seguridad/handoff/carga) -- eso ya esta parcialmente cubierto (E2E+carga por
e2e_http/e2e_support_ai_chat_test.ps1, handoff/integracion por
support/tests.py). Este directorio cubre especificamente la logica pura del
motor (action_graph.py/retrievers.py) que antes no tenia ninguna red de
regresion.

Requiere las dependencias de requirements.txt (langchain/langgraph/etc.)
instaladas -- correr dentro del contenedor `sintel_ai`:
    docker compose exec sintel_ai pytest ai_engine/tests -v
No se pudo ejecutar esta suite en la sesion que la escribio (host sin
langchain/langgraph instalados) -- verificar en el contenedor antes de
confiar en que compila y pasa.
"""
import sys
from pathlib import Path

import pytest

# Los modulos de ai_engine se importan "planos" (from auth import ...,
# from tools.metadata import ...), igual que hace main.py -- se asume
# ai_engine/ en la raiz del sys.path, no un paquete instalado.
AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))


@pytest.fixture(autouse=True)
async def _flush_tool_rate_limits():
    """
    El rate limiter por-Tool vive en Redis desde el 2026-08-17 (Fase 23, ver
    action_graph.py::_rate_limit_exceeded) -- antes era un deque en memoria del
    proceso, que se reseteaba solo en cada corrida de pytest. Redis persiste entre
    corridas: varios tests (test_policy_layer.py, test_security_adversarial.py)
    usan un user_id fijo (ej. 1) contra capabilities con rate_limit declarado
    (abrir_ticket_soporte, crear_alquiler, etc.) -- sin este flush, esos tests
    acumularian hits de corridas anteriores y fallarian solos con el tiempo, sin
    ningun cambio real de codigo. autouse=True: mas simple y a prueba de olvidos
    que agregar cleanup manual a cada test nuevo que toque una Tool con rate_limit.
    """
    import redis.asyncio as aredis
    from config import CHECKPOINTER_REDIS_URL
    client = aredis.Redis.from_url(CHECKPOINTER_REDIS_URL, decode_responses=True)
    try:
        keys = [k async for k in client.scan_iter(match="ai:tool_rate:*")]
        if keys:
            await client.delete(*keys)
    except Exception:
        pass  # Redis no disponible en este entorno -- no debe tumbar la suite entera
    finally:
        await client.aclose()
    yield
