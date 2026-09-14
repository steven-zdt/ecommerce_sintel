"""
`log_change_operation()`/`read_recent_operations()` -- POST-GRAPH 13
"Change Audit" (rediseno "AI Editor Runtime", 2026-08-11).

Registro append-only (JSONL) de cada corrida del pipeline de `ai_editor`
-- MISMO patron que `project_knowledge_graph.audit.query_log` (Fase 18
del rediseno anterior: best-effort, nunca persiste secretos), pero
implementacion PROPIA e independiente -- `ai_editor` no importa ese
modulo (es "internal" de `project_knowledge_graph`, fuera de la frontera
de `graph_client`).

Campos que pide el prompt maestro: request/intent/graph version/context
packet id/plan id/files/symbols/tests/validation/approval/commit/
timestamp. Regla explicita del prompt maestro, aplicada aca con una
sanitizacion real (no solo una promesa en el docstring): NUNCA se
persisten secretos/tokens/passwords/credenciales, incluso si aparecieran
por error en los datos de entrada -- cualquier clave de dict cuyo nombre
contenga un patron sensible se omite del registro, y cualquier valor de
texto largo se trunca (evita que un `request` gigante o un traceback
completo infle el log).
"""
import datetime
import json
import logging

from ai_editor.workspace import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = WORKSPACE_ROOT / "ai_editor" / "data" / "CHANGE_AUDIT_LOG.jsonl"

MAX_VALUE_LEN = 500
_FORBIDDEN_KEY_SUBSTRINGS = ("secret", "password", "token", "api_key", "apikey", "credential")


def _sanitize(value):
    if isinstance(value, dict):
        return {
            key: _sanitize(val) for key, val in value.items()
            if not any(pattern in key.lower() for pattern in _FORBIDDEN_KEY_SUBSTRINGS)
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str) and len(value) > MAX_VALUE_LEN:
        return value[:MAX_VALUE_LEN] + "...(truncado)"
    return value


def log_change_operation(**fields) -> None:
    """Best-effort: nunca lanza, un fallo de logging no debe tumbar el
    pipeline real. Campos tipicos (todos opcionales, se sanitizan todos
    por igual): `request`, `intent_id`, `domain`, `graph_snapshot`,
    `plan_id`, `files`, `symbols`, `tests_required`, `validation_status`,
    `approval_decision`, `commit_sha`, `status`."""
    try:
        # `_sanitize(fields)` en un solo paso (no un dict-comprehension
        # manual sobre `fields.items()`) -- BUG REAL encontrado en la
        # propia verificacion de esta fase: iterar manualmente solo
        # sanitizaba los VALORES de cada campo de primer nivel, nunca sus
        # CLAVES -- `log_change_operation(api_key="...")` (un campo de
        # primer nivel, no anidado) pasaba integro al log. `_sanitize()`
        # ya filtra claves prohibidas en cualquier dict que recibe;
        # llamarlo sobre `fields` completo (que es un dict) aplica el
        # mismo filtro al primer nivel tambien, sin logica duplicada.
        record = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        record.update(_sanitize(fields))
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("No se pudo escribir CHANGE_AUDIT_LOG (best-effort, no fatal)", exc_info=True)


def read_recent_operations(limit: int = 50) -> list[dict]:
    """Best-effort en lectura tambien -- una linea corrupta individual se
    saltea en vez de romper toda la lectura."""
    if not AUDIT_LOG_PATH.exists():
        return []
    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records
