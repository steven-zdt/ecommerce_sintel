"""
Deteccion de que apps/frontend cambiaron: git diff primero, hash de archivos
como fallback. Extraido de ai_engine/incremental_updater.py::detect_changed_apps
/_parse_git_diff/_detect_via_hashes (Fase 7, PLAN_MAESTRO_DE_SEPARACION_
PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).

Fase 15 "Incremental Semantic Graph" (Site Knowledge Graph, 2026-08-10)
agrega `detect_changed_symbols()`/`symbols_touched_by_diff()`: el nivel de
detalle que pide el plan es `git diff -> changed files -> changed symbols`,
no solo `changed files -> changed apps` (lo que ya existia). **Alcance
deliberado, documentado, no una implementacion completa del "REQUISITO" del
plan**: esto agrega DETECCION a nivel de simbolo (que funciones especificas
tocan las lineas modificadas), pero el REBUILD del Knowledge Graph
(`_rebuild_derived_artifacts()` en `updater.py`) sigue siendo del grafo
COMPLETO -- convertir `KnowledgeGraphBuilder` en un builder que solo
recalcula el subgrafo de los simbolos afectados (en vez de reconstruir los
9575 nodos desde cero) es un cambio de arquitectura mucho mayor (tocaria
cada `_link_*`/`_infer_*` del builder para soportar actualizacion parcial),
fuera de alcance de esta pasada -- documentado como limitacion real
pendiente, no resuelta en silencio.
"""
import logging
import re
import subprocess
from pathlib import Path

from project_knowledge_graph.config import BASE_DIR, DJANGO_APPS
from project_knowledge_graph.incremental.hashing import (
    collect_app_files,
    collect_frontend_files,
    hash_file,
    load_hash_db,
    save_hash_db,
)

logger = logging.getLogger(__name__)


def detect_changed_apps() -> tuple[list[str], bool]:
    """Devuelve (changed_app_names, frontend_changed). Usa git diff si esta
    disponible, cae a comparacion de hashes de archivo si no."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(BASE_DIR.parent), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return _parse_git_diff(result.stdout.strip().splitlines())
    except (OSError, subprocess.SubprocessError):
        pass

    return _detect_via_hashes()


def _parse_git_diff(changed_files: list[str]) -> tuple[list[str], bool]:
    apps = set()
    frontend_changed = False
    for f in changed_files:
        parts = Path(f).parts
        if not parts:
            continue
        # ecommerce_sintel/{app}/... structure
        if len(parts) >= 2 and parts[0] == "ecommerce_sintel":
            if parts[1] in DJANGO_APPS:
                apps.add(parts[1])
            elif parts[1] == "frontend":
                frontend_changed = True
    return list(apps), frontend_changed


def _detect_via_hashes() -> tuple[list[str], bool]:
    hash_db = load_hash_db()
    new_db: dict[str, str] = {}
    changed_apps: set[str] = set()
    frontend_changed = False

    for app_name in DJANGO_APPS:
        for path in collect_app_files(app_name):
            key = str(path)
            new_hash = hash_file(path)
            new_db[key] = new_hash
            if hash_db.get(key) != new_hash:
                changed_apps.add(app_name)

    for path in collect_frontend_files():
        key = str(path)
        new_hash = hash_file(path)
        new_db[key] = new_hash
        if hash_db.get(key) != new_hash:
            frontend_changed = True

    save_hash_db(new_db)
    return list(changed_apps), frontend_changed


# ---- Symbol-level diff (Fase 15, Site Knowledge Graph, 2026-08-10) --------

_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_DIFF_FILE_HEADER_RE = re.compile(r"^\+\+\+ b/(.+)$")


def parse_diff_hunks(diff_text: str) -> list[dict]:
    """Parsea un `git diff -U0`-style unified diff a `[{"file": path,
    "start_line": N, "end_line": M}, ...]` por hunk, usando el lado NUEVO
    (`+`) de cada `@@ -a,b +c,d @@` -- esas son las lineas reales en el
    archivo actual, lo que necesitamos para cruzar contra
    `Symbol.start_line`/`end_line`. `path` queda relativo al repo (`b/`
    strip), consistente con `str(Path(f).parts)` que ya usa
    `_parse_git_diff()`."""
    hunks = []
    current_file: str | None = None
    for line in diff_text.splitlines():
        file_m = _DIFF_FILE_HEADER_RE.match(line)
        if file_m:
            current_file = file_m.group(1)
            continue
        hunk_m = _HUNK_HEADER_RE.match(line)
        if hunk_m and current_file:
            start = int(hunk_m.group(1))
            count = int(hunk_m.group(2)) if hunk_m.group(2) is not None else 1
            # count==0 (hunk de solo-borrado, `+0,0`) no toca ninguna linea
            # nueva -- no hay simbolo "actual" que cruzar, se omite.
            if count > 0:
                hunks.append({"file": current_file, "start_line": start, "end_line": start + count - 1})
    return hunks


def get_git_diff_text() -> str:
    """`git diff -U0 HEAD` real -- 0 lineas de contexto (solo lo que
    realmente cambio), mas facil de parsear que el default de 3 lineas de
    contexto.

    [CORREGIDO -- bug real encontrado, no una reescritura preventiva]:
    `text=True` sin `encoding=` explicito usa la codepage ANSI del sistema
    en Windows (cp1252) para decodificar stdout -- `git diff -U0` incluye
    el CONTENIDO real del codigo (a diferencia de `_parse_git_diff()`
    arriba, que solo pide `--name-only`), y este proyecto tiene comentarios/
    strings en español con acentos reales (UTF-8) por todo el codebase.
    Verificado real: `UnicodeDecodeError: 'charmap' codec can't decode byte
    0x8d` al correr esto contra el repo real. Corregido con `encoding=
    "utf-8", errors="replace"` -- mismo criterio que `read_text(encoding=
    "utf-8", errors="replace")`, el patron establecido en todo el resto de
    este modulo para leer contenido de texto real del repo."""
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", "--no-color", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(BASE_DIR.parent), timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def symbols_touched_by_diff(hunks: list[dict]) -> list[dict]:
    """Cruza los hunks (rangos de linea reales) contra `Symbol.start_line`/
    `end_line` del Knowledge Graph YA CONSTRUIDO (no reconstruye nada) --
    un Symbol "toca" un hunk si sus rangos de linea se solapan. Normaliza
    el path del diff (relativo al repo completo, `ecommerce_sintel/...`)
    al path relativo a `ecommerce_sintel/` que usan los nodos `Symbol`
    (`BASE_DIR`), mismo criterio que `_parse_git_diff()`."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

    kg = get_knowledge_graph()
    symbols_by_file: dict[str, list] = {}
    for sym in kg.nodes_of_type("Symbol"):
        symbols_by_file.setdefault(sym.file, []).append(sym)

    touched = []
    for hunk in hunks:
        parts = Path(hunk["file"]).parts
        if not (len(parts) >= 2 and parts[0] == "ecommerce_sintel"):
            continue
        rel_path = "/".join(parts[1:])
        for sym in symbols_by_file.get(rel_path, []):
            sym_start = sym.meta.get("start_line")
            sym_end = sym.meta.get("end_line")
            if sym_start is None or sym_end is None:
                continue
            if sym_start <= hunk["end_line"] and hunk["start_line"] <= sym_end:
                touched.append(sym.to_dict())
    return touched


def detect_changed_symbols() -> list[dict]:
    """Punto de entrada real: `git diff -U0 HEAD` -> hunks -> Symbol nodes
    reales tocados. Devuelve `[]` si no hay diff (nada que reportar) o si
    `git` no esta disponible -- mismo fallback silencioso que
    `detect_changed_apps()` ya tenia para el caso sin git."""
    diff_text = get_git_diff_text()
    if not diff_text:
        return []
    hunks = parse_diff_hunks(diff_text)
    if not hunks:
        return []
    return symbols_touched_by_diff(hunks)
