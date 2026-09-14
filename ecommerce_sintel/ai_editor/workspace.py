"""
`WORKSPACE_ROOT`/`resolve_workspace_path()` -- utilidad compartida de
`ai_editor`, usada desde POST-GRAPH 5 en adelante (rediseno "AI Editor
Runtime", 2026-08-11).

Raiz del workspace real que `ai_editor` tiene permitido tocar
(`ecommerce_sintel/`) -- resuelta de forma INDEPENDIENTE de
`project_knowledge_graph.config.BASE_DIR` (misma ubicacion fisica hoy,
pero calculada por su cuenta: el resto de `ai_editor` no debe importar
`project_knowledge_graph.config` ni ningun otro modulo "interno" de ese
paquete, solo `graph_client`, ver `ai_editor/__init__.py` "REGLA
ARQUITECTONICA ABSOLUTA").

`resolve_workspace_path()` es la base que POST-GRAPH 18 "Hardening"
(restricciones de path traversal / escritura fuera del workspace)
extendera -- se construye aca, en la primera fase que necesita
efectivamente tocar el filesystem real (verificar que un archivo del
grafo sigue existiendo en disco), en vez de posponerla hasta que ya haya
codigo de escritura que proteger retroactivamente.
"""
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC_ROOT = WORKSPACE_ROOT / "frontend" / "src"

# Raiz del repo GIT externo (padre de WORKSPACE_ROOT) -- NUNCA un root
# escribible por ai_editor, solo existe para poder verificar la existencia
# real de nodos `Documentation` (bug real encontrado durante FASE 24 del
# plan "AI Change Proposal Engine", 2026-08-11): `project_knowledge_graph.
# knowledge_graph.enrichers.documentation` guarda `Documentation.file`
# relativo al repo GIT completo (`REPO_ROOT` ahi, parents[4] de ese
# archivo), no relativo a `WORKSPACE_ROOT` -- por eso, a diferencia de
# `Symbol`/`File`/`Endpoint` (siempre relativos a `WORKSPACE_ROOT` o a
# `FRONTEND_SRC_ROOT`), un path de `Documentation` como
# `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` vive
# fisicamente FUERA de `WORKSPACE_ROOT` (ese doc en particular vive un
# nivel arriba). Usar solo para lectura/validacion (`validate_plan()`),
# nunca pasarlo como `base_root` de `resolve_repo_file()` ni de ninguna
# funcion de `patch/`/`repository/` -- el limite de escritura de todo
# `ai_editor` sigue siendo estrictamente `WORKSPACE_ROOT`.
REPO_ROOT = WORKSPACE_ROOT.parent


class WorkspaceViolation(RuntimeError):
    """Un path relativo intenta resolver fuera de `WORKSPACE_ROOT` (ej.
    `../../etc/passwd`, o un path absoluto de otro drive)."""


def _resolve_under(root: Path, relative_path: str, *, boundary: Path | None = None) -> Path:
    """`boundary` es el limite anti-traversal real -- por default el
    mismo `root` (el caso comun), pero POST-GRAPH 12 (`promote_to_
    workspace`, pensado para poder apuntarse a un `workspace_root` de
    PRUEBA en vez del real) necesita poder pasar una raiz custom sin
    perder la verificacion de que el resultado no escapa de ESA raiz."""
    effective_boundary = boundary if boundary is not None else root
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(effective_boundary.resolve())
    except ValueError:
        raise WorkspaceViolation(f"'{relative_path}' resuelve fuera de {effective_boundary}")
    return candidate


def resolve_workspace_path(relative_path: str) -> Path:
    """Resuelve `relative_path` relativo a `WORKSPACE_ROOT`
    (`ecommerce_sintel/`) -- el caso BACKEND (ej. `renting/api/views.py`).
    Lanza `WorkspaceViolation` si el resultado cae fuera de
    `WORKSPACE_ROOT`, nunca lo permite en silencio."""
    return _resolve_under(WORKSPACE_ROOT, relative_path)


def resolve_repo_file(relative_path: str, base_root: Path | None = None) -> Path | None:
    """Encuentra el archivo REAL correspondiente a `relative_path` tal
    como aparece en `Symbol.file`/`File.file` del grafo -- que puede
    estar expresado relativo a `base_root` (default `WORKSPACE_ROOT`,
    paths de backend, ej. `renting/api/views.py`) O relativo a
    `base_root/frontend/src/` (paths de frontend, ej. `views/customer/
    renting/RentalCatalogView.vue` -- **defecto real encontrado en
    POST-GRAPH 5**: el scanner de frontend guarda el path relativo a
    `FRONTEND_DIR = BASE_DIR/frontend/src`, no a `BASE_DIR`, y el tipo de
    nodo/`app` no distingue esto de forma confiable en todos los casos).
    En vez de una heuristica fragil por tipo de nodo, se prueban AMBAS
    raices contra el disco real y se usa la que exista -- devuelve `None`
    si ninguna existe. `base_root` explicito (POST-GRAPH 12,
    `promote_to_workspace`) permite apuntar esta misma resolucion a un
    workspace de PRUEBA en vez del real, sin duplicar la logica dual
    backend/frontend en otro archivo."""
    root = base_root if base_root is not None else WORKSPACE_ROOT
    backend_path = _resolve_under(root, relative_path, boundary=root)
    if backend_path.exists():
        return backend_path
    frontend_path = _resolve_under(root, str(Path("frontend") / "src" / relative_path), boundary=root)
    if frontend_path.exists():
        return frontend_path
    return None


def resolve_repo_doc_path(relative_path: str) -> Path | None:
    """Version de solo-lectura de `resolve_repo_file()` para nodos
    `Documentation` -- prueba `relative_path` contra `REPO_ROOT`, no contra
    `WORKSPACE_ROOT`. Devuelve `None` si no existe. NUNCA usar el resultado
    como destino de escritura (ver docstring de `REPO_ROOT`)."""
    try:
        candidate = _resolve_under(REPO_ROOT, relative_path, boundary=REPO_ROOT)
    except WorkspaceViolation:
        return None
    return candidate if candidate.exists() else None
