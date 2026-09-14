"""
Fingerprint de contenido -- POST-GRAPH 6 "Patch Engine" (rediseno "AI
Editor Runtime", 2026-08-11). `sha256` sobre el texto EXACTO de un rango
de lineas real -- la "PROTECCION" que pide el prompt maestro: antes de
modificar, el hash actual debe coincidir con el hash esperado (calculado
cuando se genero el plan), o se aborta. Evita aplicar un patch sobre
codigo que cambio mientras el plan se generaba/aprobaba.
"""
import hashlib
from pathlib import Path


def compute_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_lines_fingerprint(path: Path, line_start: int, line_end: int) -> str | None:
    """Lee el rango `[line_start, line_end]` (1-indexed, inclusive) REAL
    de `path` y devuelve su fingerprint -- `None` si el archivo no existe
    o el rango es invalido (nunca lanza, el llamador decide como tratar
    `None`)."""
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if line_start < 1 or line_end > len(lines) or line_start > line_end:
        return None
    return compute_fingerprint("".join(lines[line_start - 1:line_end]))
