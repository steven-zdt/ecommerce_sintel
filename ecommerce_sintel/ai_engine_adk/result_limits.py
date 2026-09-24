"""
HARDENING F12/C4 (2026-09-24) -- tope del resultado de una Tool que vuelve al modelo.

Propuesta: ai_engine_adk/.AGENT/HARDENING_F12_PROPOSAL_2026-09-24.md. Con num_ctx=4096 en Ollama, un listado grande de catalogo puede
llenar el contexto. `limit_result` es PURO y determinista (stdlib): si el JSON serializado excede `max_chars` recorta la lista mas larga
(conservando el orden, con un marcador explicito para que el modelo no invente el resto) y acorta cadenas gigantes. No cambia la forma
del resultado salvo por el marcador `_truncated` (dict) o un ultimo elemento marcador (lista de nivel superior).
"""
import copy
import json

TRUNC_SUFFIX = " ...[recortado]"


def _size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str))


def _longest_list(value, path=()):
    """(ruta, lista) de la lista mas larga (por numero de elementos) en cualquier nivel; None si no hay listas."""
    best = None
    if isinstance(value, list):
        best = (path, value)
        children = enumerate(value)
    elif isinstance(value, dict):
        children = value.items()
    else:
        return None
    for key, child in children:
        found = _longest_list(child, path + (key,))
        if found and (best is None or len(found[1]) > len(best[1])):
            best = found
    return best


def _get(root, path):
    for key in path:
        root = root[key]
    return root


def _cap_strings(value, cap):
    if isinstance(value, str):
        return value if len(value) <= cap else value[: max(0, cap - len(TRUNC_SUFFIX))] + TRUNC_SUFFIX
    if isinstance(value, list):
        return [_cap_strings(v, cap) for v in value]
    if isinstance(value, dict):
        return {k: _cap_strings(v, cap) for k, v in value.items()}
    return value


def limit_result(result, max_chars: int):
    """Devuelve (resultado_acotado, info | None). info = {original_chars, final_chars, shown, total, strings_capped}; None si ya cabia."""
    if not isinstance(result, (dict, list)) or max_chars <= 0:
        return result, None
    original = _size(result)
    if original <= max_chars:
        return result, None

    out = copy.deepcopy(result)
    shown = total = None
    found = _longest_list(out)
    if found and len(found[1]) > 1:
        path, items = found
        total = len(items)
        lo, hi = 1, total  # mayor k tal que el resultado con k elementos cabe; k=1 como minimo
        while lo < hi:
            mid = (lo + hi + 1) // 2
            items_backup = items[:]
            items[:] = items_backup[:mid]
            fits = _size(out) <= max_chars
            items[:] = items_backup
            lo, hi = (mid, hi) if fits else (lo, mid - 1)
        shown = lo
        del items[shown:]
        marker = {"shown": shown, "total": total}
        if path == ():
            items.append({"_truncated": marker})
        else:
            parent = _get(out, path[:-1]) if len(path) > 1 else out
            if isinstance(parent, dict):
                parent["_truncated"] = marker
    strings_capped = False
    if _size(out) > max_chars:
        out = _cap_strings(out, max(200, max_chars // 2))
        strings_capped = True
    return out, {"original_chars": original, "final_chars": _size(out), "shown": shown, "total": total,
                 "strings_capped": strings_capped}
