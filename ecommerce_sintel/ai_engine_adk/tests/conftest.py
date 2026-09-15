"""
Mision RAG-POST2 (FASE 7, 2026-09-16): fuerza ADK_SESSION_BACKEND=memory para
TODA la suite, sin importar que el entorno real (docker-compose.yml) traiga
ADK_SESSION_BACKEND=database via env_file/environment -- conftest.py se
importa antes que cualquier modulo de test, así que esto corre antes que
sintel_root_workflow.py construya `_session_service` a nivel de modulo.

Sin esto, `docker compose run --rm --no-deps sintel_ai_adk pytest tests/`
(el comando real que usa esta suite, ver AUDITORIA/RAG_POST2_BASELINE.md)
intentaria conectar a un Postgres que --no-deps nunca arranca -- rompiendo
decenas de tests que hoy no tienen nada que ver con sesion persistente. Los
tests DEDICADOS a DatabaseSessionService (test_persistent_session.py) corren
aparte, CON deps reales (`docker compose run --rm sintel_ai_adk pytest
tests/test_persistent_session.py`, sin --no-deps), documentado en ese mismo
archivo.
"""
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ["ADK_SESSION_BACKEND"] = "memory"


@pytest.fixture(autouse=True)
def _default_customer_memory_mocks(request):
    """Mision RAG-POST2 (FASE 10-11, 2026-09-16): sintel_root_workflow.py
    ahora llama a fetch_customer_memories()/extract_and_store_memory() en
    CADA turno -- sin este default, cada test de la suite (la gran mayoria
    no relacionados con memoria) intentaria una llamada HTTP real a Django,
    que --no-deps nunca arranca. Mismo problema de fondo que resolvio
    ADK_SESSION_BACKEND=memory arriba, aplicado a esta fase.

    tests/test_customer_memory.py (dedicado) desactiva este default -- prueba
    el comportamiento REAL, con sus propios patches explicitos por caso."""
    if Path(request.node.fspath).name == "test_customer_memory.py":
        yield
        return
    with patch("sintel_root_workflow.fetch_customer_memories", new=AsyncMock(return_value=[])), \
         patch("sintel_root_workflow.extract_and_store_memory", new=AsyncMock(return_value=None)):
        yield
