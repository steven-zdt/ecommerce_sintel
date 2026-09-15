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

os.environ["ADK_SESSION_BACKEND"] = "memory"
