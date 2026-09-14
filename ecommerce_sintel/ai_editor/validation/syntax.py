"""
Nivel 1 de POST-GRAPH 8 "Validation Engine" (rediseno "AI Editor
Runtime", 2026-08-11) -- verificacion de SINTAXIS sobre archivos de un
sandbox ya parcheado (POST-GRAPH 6/7). Nunca ejecuta el codigo, solo lo
parsea/compila.

Python: `ast.parse()` real (libreria estandar, sin dependencias nuevas).
JS/TS: `node --check <archivo>` -- shell-out real pero SEGURO: `--check`
solo parsea y reporta errores de sintaxis, nunca ejecuta el archivo.
Vue: no hay parser real de Vue SFC disponible (mismo limite ya
documentado en `project_knowledge_graph` para el escaneo de frontend) --
se extrae SOLO el bloque `<script>` con una regex propia (NO se importa
nada de `project_knowledge_graph.scanner.frontend_scanner`, que es
"internal" segun la regla de frontera de `ai_editor`) y se valida ese
fragmento con `node --check`. El `<template>` no se valida a este nivel.
"""
import ast
import re
import subprocess
import tempfile
from pathlib import Path

_VUE_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL)


def check_python_syntax(path: Path) -> tuple[bool, str]:
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        return True, "sintaxis Python valida"
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"


def check_js_syntax(path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["node", "--check", str(path)], capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return True, "SKIPPED -- node no disponible en este entorno"
    except subprocess.TimeoutExpired:
        return False, "timeout verificando sintaxis JS"
    if result.returncode == 0:
        return True, "sintaxis JS valida (node --check)"
    return False, f"node --check fallo: {result.stderr.strip()[:300]}"


def check_vue_syntax(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _VUE_SCRIPT_RE.search(text)
    if not match:
        return True, "sin bloque <script> que validar"

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(match.group(1))
        tmp_path = Path(tmp.name)
    try:
        return check_js_syntax(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def check_syntax(sandbox_root: Path, relative_path: str) -> tuple[bool, str]:
    """Punto de entrada: elige el validador segun la extension real del
    archivo dentro del sandbox. `True` para extensiones sin validador
    conocido (no es un fallo -- simplemente no hay nada que chequear a
    este nivel para ese tipo de archivo)."""
    real_path = Path(sandbox_root) / relative_path
    if not real_path.exists():
        return True, "archivo no existe en el sandbox (nada que validar, ej. resultado de un DELETE)"

    suffix = real_path.suffix
    if suffix == ".py":
        return check_python_syntax(real_path)
    if suffix == ".vue":
        return check_vue_syntax(real_path)
    if suffix in (".js", ".ts"):
        return check_js_syntax(real_path)
    return True, f"sin validador de sintaxis para '{suffix}' -- omitido"
