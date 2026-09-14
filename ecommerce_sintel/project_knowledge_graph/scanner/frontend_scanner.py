"""
Scanner especifico de frontend (Vue/JS) -- interpreta componentes, stores,
router y sus relaciones (llamadas API, imports). Extraido de ai_engine/
auditor.py (Fase 4, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH,
2026-08-08). Extendido Fase 3 (Site Knowledge Graph, 2026-08-10) con
extract_frontend_symbols()/isolate_vue_script() para granularidad de
funcion dentro de .vue/.js/.ts -- ver extract_frontend_symbols() para el
detalle de que se extrae y por que (no hay parser JS real disponible en este
proyecto, ver docstring de esa funcion).
"""
import hashlib
import re
from pathlib import Path

from project_knowledge_graph.config import VUE_ROLE_PATTERNS


def detect_vue_role(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/")
    for role, pattern in VUE_ROLE_PATTERNS:
        if pattern.search(rel):
            return role
    ext = Path(rel).suffix
    if ext == ".vue":
        return "component"
    if ext in (".js", ".ts"):
        return "script"
    return "misc"


def extract_vue_api_calls(content: str) -> list[dict]:
    """Extract api.get/post/patch/delete/put calls and their URL patterns.

    [ACTUALIZADO Fase 4, 2026-08-10] Agregado el patron encadenado
    `useApi().get(url)` -- verificado contra el repo real: los 10 archivos
    de `services/**/*.js` (la capa real de "custom API wrapper" del
    proyecto, ej. `availabilityService.js`) usan ESTE patron encadenado
    exclusivamente (69 ocurrencias reales), nunca `const api = useApi();
    api.get(...)`. Sin este patron, la capa de servicios completa quedaba
    invisible para CONSUMES_ENDPOINT -- 0 llamadas API detectadas en esos
    10 archivos antes de este fix."""
    calls = []
    patterns = [
        re.compile(r'api\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]'),
        re.compile(r'useApi\(\)\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]'),
        re.compile(r'axios\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]'),
        re.compile(r'(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+api[^`\'"]+)[`\'"]'),
    ]
    for pat in patterns:
        for m in pat.finditer(content):
            method, url = m.group(1).upper(), m.group(2)
            calls.append({"method": method, "url": url})
    return calls


_USE_HOOK_CALL_RE = re.compile(r"\b(use[A-Z]\w*)\s*\(")


def extract_use_hook_calls(content: str) -> list[str]:
    """Nombres de hooks `useX(...)` realmente LLAMADOS (no solo importados)
    en el contenido dado -- deduplicado, orden de aparicion. Reemplaza a la
    antigua `extract_vue_store_imports()` [RETIRADA Fase 4, 2026-08-10]: esa
    funcion capturaba solo el sufijo despues de "use" (`use(\\w+Store)` ->
    "AvailabilityStore" para `useAvailabilityStore()`) e intentaba matchear
    eso como substring contra el `store_id` real del store (`rentalAvailability`
    para ese mismo store) -- nombres estructuralmente no relacionados por
    convencion de este proyecto (el hook se nombra por el dominio, el
    store_id es un slug corto elegido aparte). Resultado verificado contra
    el repo real: **0 aristas USES_STORE en todo el proyecto**, en las ~520
    archivos frontend escaneados -- la logica nunca funciono, no es una
    regresion de esta fase. El fix real vive en `knowledge_graph/builder.py`:
    esta funcion devuelve el nombre COMPLETO del hook tal como se llama
    (`useAvailabilityStore`, `useToast`, ...) y el builder lo matchea de
    forma EXACTA contra `hook_name` real de cada PiniaStore (capturado en
    `extract_pinia_store()`) o contra el nombre de archivo de cada
    Composable -- sin heuristica de substring en ninguno de los dos lados."""
    seen: set[str] = set()
    names: list[str] = []
    for m in _USE_HOOK_CALL_RE.finditer(content):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def extract_vue_component_imports(content: str) -> list[str]:
    components = []
    pat = re.compile(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+\.vue)['\"]")
    for m in pat.finditer(content):
        components.append(m.group(1))
    return list(set(components))


def extract_vue_template_tags(content: str) -> list[str]:
    """Tags de componente usados en el <template>, PascalCase o kebab-case --
    necesario porque este proyecto usa auto-import de componentes. Sin esto,
    todo componente auto-importado aparece como "codigo muerto" por error."""
    tags = set()
    for m in re.finditer(r"<([A-Z][A-Za-z0-9]*)\b", content):
        tags.add(m.group(1))
    for m in re.finditer(r"<([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b", content):
        tags.add("".join(part.capitalize() for part in m.group(1).split("-")))
    return sorted(tags)


def extract_vue_emits_props(content: str) -> dict:
    props, emits = [], []
    props_match = re.search(r"defineProps\s*\(\s*\{([^}]+)\}", content, re.DOTALL)
    if props_match:
        for m in re.finditer(r"(\w+)\s*:", props_match.group(1)):
            props.append(m.group(1))
    emits_match = re.search(r"defineEmits\s*\(\s*\[([^\]]+)\]", content)
    if emits_match:
        for m in re.finditer(r"['\"](\w+)['\"]", emits_match.group(1)):
            emits.append(m.group(1))
    return {"props": props, "emits": emits}


_STORE_HOOK_NAME_RE = re.compile(r"export\s+const\s+(use\w+)\s*=\s*defineStore")


def extract_pinia_store(content: str) -> dict | None:
    id_match = re.search(r"defineStore\s*\(\s*['\"](\w+)['\"]", content)
    hook_match = _STORE_HOOK_NAME_RE.search(content)
    state_match = re.search(r"state:\s*\(\s*\)\s*=>\s*\(\s*\{([^}]+)\}", content, re.DOTALL)
    actions = re.findall(r"async\s+(\w+)\s*\(|^\s+(\w+)\s*\([^)]*\)\s*\{", content, re.MULTILINE)
    if not id_match:
        return None
    return {
        "store_id": id_match.group(1),
        # hook_name (Fase 4, 2026-08-10): nombre real del hook exportado
        # (`useAvailabilityStore`), usado por builder.py para matchear
        # EXACTO contra extract_use_hook_calls() del lado consumidor --
        # store_id (arriba) es un slug de negocio sin relacion textual
        # garantizada con el nombre del hook, no sirve para matching.
        "hook_name": hook_match.group(1) if hook_match else None,
        "state_keys": [m.group(1) for m in re.finditer(r"(\w+)\s*:", state_match.group(1))] if state_match else [],
        "actions": [a[0] or a[1] for a in actions if a[0] or a[1]],
    }


def extract_router_component_aliases(content: str) -> dict[str, str]:
    """Mapea cada alias local de import (lazy o estatico) a la ruta real del
    .vue que carga -- sin esto, `component:` puede coincidir por casualidad
    con el nombre de archivo de un componente completamente distinto."""
    aliases: dict[str, str] = {}
    for m in re.finditer(
        r"(?:const|let|var)\s+(\w+)\s*=\s*\(\)\s*=>\s*import\(\s*['\"]([^'\"]+\.vue)['\"]\s*\)",
        content,
    ):
        aliases[m.group(1)] = m.group(2)
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+['\"]([^'\"]+\.vue)['\"]",
        content,
    ):
        aliases[m.group(1)] = m.group(2)
    return aliases


_ROUTE_NAME_RE = re.compile(r"name\s*:\s*['\"](\w+)['\"]")
_ROUTE_COMPONENT_RE = re.compile(r"component\s*:\s*(\w+)")


def extract_router_routes(content: str) -> list[dict]:
    """Cada `path:` define una ventana acotada (hasta el proximo `path:` o 600
    caracteres) y `name`/`component` se buscan solo dentro de esa ventana --
    evita el problema de backtracking de un solo regex con grupos opcionales
    en modo DOTALL, sin necesitar un parser real de objetos JS."""
    routes = []
    aliases = extract_router_component_aliases(content)
    path_matches = list(re.finditer(r"path\s*:\s*['\"]([^'\"]*)['\"]", content))
    for i, m in enumerate(path_matches):
        window_end = path_matches[i + 1].start() if i + 1 < len(path_matches) else m.end() + 600
        window = content[m.end():window_end]
        name_m = _ROUTE_NAME_RE.search(window)
        comp_m = _ROUTE_COMPONENT_RE.search(window)
        path, name, comp = m.group(1), name_m.group(1) if name_m else None, \
            comp_m.group(1) if comp_m else None
        resolved_path = aliases.get(comp) if comp else None
        component_resolved = Path(resolved_path).stem if resolved_path else None
        routes.append({
            "path": path, "name": name, "component": comp,
            "component_resolved": component_resolved,
        })
    return routes


# ---- FrontendSymbol (Fase 3, Site Knowledge Graph, 2026-08-10) -------------
#
# No hay parser JS/TS real disponible en este proyecto (ni en Python -- no
# hay esprima/tree-sitter instalado -- ni como dependencia nueva, evitando
# agregar una dependencia pesada para una sola pasada de escaneo). Se aplica
# el mismo criterio pragmatico que ya usa extract_router_routes() (ventanas
# heuristicas via regex + balance de parentesis/llaves, no un AST real).
#
# Alcance deliberado, no una omision silenciosa (ver 3.2/3.3 del plan, que
# pide 9 sub-tipos): de los 9 symbol_type listados se implementan 4
# (function, computed, watch, lifecycle) mas 3 roles semanticos (api_call,
# emit, event_handler). "callback" (arg anonimo sin nombre estable) se deja
# fuera -- sin un nombre no hay qualified_name util para indexar. "method"
# en el sentido de Options API de componentes tambien se deja fuera porque
# `frontend/CLAUDE.md` prohibe Options API en componentes ("<script setup>
# siempre") -- SI se implementa para Pinia option-stores (unico lugar real
# donde el proyecto usa el patron `nombre(args) { ... }` de metodo de
# objeto), ver _extract_store_block_methods() mas abajo.

_LIFECYCLE_HOOKS = {
    "onMounted", "onUnmounted", "onBeforeMount", "onBeforeUnmount",
    "onUpdated", "onBeforeUpdate", "onActivated", "onDeactivated",
    "onErrorCaptured", "onRenderTracked", "onRenderTriggered",
}
_REACTIVITY_HOOKS = {"computed": "computed", "watch": "watch", "watchEffect": "watch"}
_JS_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "try", "function", "return",
    "else", "finally", "do", "with",
}

_API_CALL_BODY_RE = re.compile(
    r"\b(?:api|axios)\s*\.\s*(?:get|post|put|patch|delete)\s*\(|\bfetch\s*\(|\bsafeFetchJson\s*\("
)
_EMIT_BODY_RE = re.compile(r"\bemit\s*\(")
_EVENT_HANDLER_NAME_RE = re.compile(r"^(?:handle|on)[A-Z0-9]")

_SCRIPT_BLOCK_RE = re.compile(r"<script[^>]*>([\s\S]*?)</script>")

_FUNCTION_DECL_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:export\s+)?(async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{"
)
_ARROW_CONST_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(async\s+)?"
    r"(?:\([^)]*\)|\w+)\s*=>\s*\{"
)
_HOOK_ASSIGN_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:const|let)\s+(\w+)\s*=\s*(computed|watch|watchEffect)\s*\("
)
_BARE_LIFECYCLE_RE = re.compile(r"(?:^|\n)[ \t]*(on[A-Za-z]+)\s*\(")
_BARE_WATCH_RE = re.compile(r"(?:^|\n)[ \t]*(watch|watchEffect)\s*\(")
_STORE_METHOD_RE = re.compile(r"(?:^|\n)[ \t]*(async\s+)?(\w+)\s*\(([^)]*)\)\s*\{")


def isolate_vue_script(content: str) -> str:
    """Reemplaza todo lo que esta fuera de `<script>...</script>` por saltos
    de linea (mismo conteo de '\\n' que el original) para que
    extract_frontend_symbols() nunca interprete `<template>`/`<style>` --
    los numeros de linea resultantes siguen siendo absolutos respecto al
    archivo completo, sin necesitar offset separado. No-op para contenido
    sin tag `<script>` (.js/.ts, o .vue malformado)."""
    m = _SCRIPT_BLOCK_RE.search(content)
    if m is None:
        return content
    blank_before = "\n" * content[:m.start(1)].count("\n")
    blank_after = "\n" * content[m.end(1):].count("\n")
    return blank_before + content[m.start(1):m.end(1)] + blank_after


def _line_no(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _match_balanced(text: str, open_idx: int, open_ch: str, close_ch: str) -> int | None:
    """Indice del caracter de cierre correspondiente al open_ch en open_idx,
    saltando contenido dentro de strings/template literals y comentarios --
    igual criterio pragmatico que extract_router_routes() (ventana
    heuristica, no un parser real de JS). Devuelve None si el archivo
    termina sin cerrar (entrada malformada o limite del heuristico)."""
    depth = 0
    i = open_idx
    n = len(text)
    in_str: str | None = None
    while i < n:
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            nl = text.find("\n", i)
            i = nl if nl != -1 else n
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _classify_role(name: str, body: str, symbol_type: str) -> str | None:
    if _API_CALL_BODY_RE.search(body):
        return "api_call"
    if _EMIT_BODY_RE.search(body):
        return "emit"
    # symbol_type == "lifecycle" ya cubre el significado semantico de
    # onMounted/onUnmounted/... -- sin este guard, el nombre del hook
    # (empieza con "on" + mayuscula) tambien matchea el patron de nombre de
    # event_handler, duplicando la clasificacion sin agregar informacion.
    if symbol_type != "lifecycle" and _EVENT_HANDLER_NAME_RE.match(name):
        return "event_handler"
    return None


def _make_frontend_symbol(container_name: str, name: str, symbol_type: str,
                           body: str, start_line: int, end_line: int,
                           is_async: bool = False) -> dict:
    """Simetrico a python_scanner.extract_symbols(): mismo shape base (name/
    qualified_name/kind/class_name/start_line/end_line/is_async) para que
    builder.py::_add_one_file() enchufe FrontendSymbol en la MISMA maquinaria
    File->CONTAINS->Symbol y Clase->CONTAINS->metodo que ya existe para
    Python (ver comentario de scope en builder.py) -- mas los campos nuevos
    symbol_type/role/hash que pide el plan de Fase 3.

    is_entry: si el nombre del simbolo coincide con el nombre del propio
    contenedor (ej. la funcion `useOperationTracking` dentro del archivo
    useOperationTracking.js, que ES el composable), se trata como Symbol de
    nivel raiz (kind='function', sin class_name) en vez de 'method' de si
    mismo -- evita un qualified_name redundante ('useOperationTracking.
    useOperationTracking') y matchea la semantica de Python (kind='function'
    para lo que vive a nivel de modulo)."""
    is_entry = name == container_name
    return {
        "name": name,
        "qualified_name": name if is_entry else f"{container_name}.{name}",
        "kind": "function" if is_entry else "method",
        "class_name": None if is_entry else container_name,
        "symbol_type": symbol_type,
        "role": _classify_role(name, body, symbol_type),
        "start_line": start_line,
        "end_line": end_line,
        "is_async": is_async,
        "hash": hashlib.md5(body.encode("utf-8")).hexdigest(),
        # api_calls/hook_calls (Fase 4 "Contract Graph Frontend<->Backend",
        # 2026-08-10): que endpoints/hooks usa ESTE simbolo especificamente
        # (no el archivo completo) -- builder.py los convierte en aristas
        # Symbol -CONSUMES_ENDPOINT-> Endpoint / Symbol -USES_STORE|
        # USES_COMPOSABLE-> PiniaStore|Composable. Limitacion conocida y
        # documentada: un hook llamado UNA vez a nivel de script (ej. `const
        # toast = useToast()` fuera de toda funcion, patron dominante real
        # en componentes) no cae dentro del body de ningun Symbol capturado
        # -- solo se detecta cuando el hook se llama DENTRO del cuerpo de un
        # simbolo (composables enteros, o llamadas inline). El nivel de
        # archivo (ver project_scanner.py::scan_frontend_file) sigue
        # cubriendo ese caso de forma mas gruesa.
        "api_calls": extract_vue_api_calls(body),
        "hook_calls": extract_use_hook_calls(body),
    }


def _extract_store_block_methods(content: str, block_name: str, symbol_type: str,
                                  container_name: str) -> list[dict]:
    """Metodos `nombre(args) { ... }` (object-method shorthand) dentro de un
    bloque `actions: { ... }`/`getters: { ... }` de un Pinia option-store --
    unico lugar real del proyecto donde se usa ese patron (ver
    frontend/CLAUDE.md: componentes son <script setup> siempre, Options API
    prohibido para componentes; los stores Pinia SI son option-style,
    verificado contra availabilityStore.js/cart.js/auth.js reales)."""
    block_m = re.search(rf"\b{block_name}\s*:\s*\{{", content)
    if block_m is None:
        return []
    block_open = block_m.end() - 1
    block_close = _match_balanced(content, block_open, "{", "}")
    if block_close is None:
        return []
    block_text = content[block_open:block_close]

    symbols = []
    claimed: list[tuple[int, int]] = []
    for m in _STORE_METHOD_RE.finditer(block_text):
        if any(s < m.end() and m.start() < e for s, e in claimed):
            continue
        name = m.group(2)
        if name in _JS_KEYWORDS:
            continue
        brace_idx = m.end() - 1
        end_idx = _match_balanced(block_text, brace_idx, "{", "}")
        if end_idx is None:
            continue
        body = block_text[brace_idx:end_idx]
        # Offset absoluto: block_open ya apunta al '{' del bloque dentro de
        # `content`, block_text es un slice desde ahi -- sumar block_open
        # devuelve la posicion real en el archivo completo.
        symbols.append(_make_frontend_symbol(
            container_name, name, symbol_type, body,
            _line_no(content, block_open + m.start(2)),
            _line_no(content, block_open + end_idx),
            is_async=bool(m.group(1)),
        ))
        claimed.append((m.start(), end_idx))
    return symbols


_EXPORTED_CONST_OBJECT_RE = re.compile(r"(?:^|\n)[ \t]*export\s+const\s+\w+\s*=\s*\{")


def _extract_flat_exported_object_methods(content: str, container_name: str) -> list[dict]:
    """Metodos `nombre(args) { ... }` declarados directo dentro de un objeto
    exportado plano -- `export const xService = { check(...) {...}, ... }`
    -- el patron real de la capa de "custom API wrapper" de este proyecto
    (`frontend/src/services/**/*.js`, verificado contra 10 archivos reales,
    ej. `services/renting/availabilityService.js`), que FASE 4 del plan
    pide cubrir explicitamente (4.1: "no asumir un unico cliente"). No
    matchea `export const useXStore = defineStore('id', {` (el `=` va
    seguido de `defineStore(`, no de `{` directo) -- sin overlap con
    `_extract_store_block_methods()`, que cubre la forma anidada
    `actions:`/`getters:` de un Pinia option-store. Se corre siempre (no
    detras de un flag de role) porque el costo de intentarlo y no encontrar
    nada es un solo regex fallido -- y porque cualquier objeto exportado
    plano con metodos reales (no solo `services/`) es informacion util."""
    m = _EXPORTED_CONST_OBJECT_RE.search(content)
    if m is None:
        return []
    obj_open = m.end() - 1
    obj_close = _match_balanced(content, obj_open, "{", "}")
    if obj_close is None:
        return []
    obj_text = content[obj_open:obj_close]

    symbols = []
    claimed: list[tuple[int, int]] = []
    for mm in _STORE_METHOD_RE.finditer(obj_text):
        if any(s < mm.end() and mm.start() < e for s, e in claimed):
            continue
        name = mm.group(2)
        if name in _JS_KEYWORDS:
            continue
        brace_idx = mm.end() - 1
        end_idx = _match_balanced(obj_text, brace_idx, "{", "}")
        if end_idx is None:
            continue
        body = obj_text[brace_idx:end_idx]
        symbols.append(_make_frontend_symbol(
            container_name, name, "function", body,
            _line_no(content, obj_open + mm.start(2)),
            _line_no(content, obj_open + end_idx),
            is_async=bool(mm.group(1)),
        ))
        claimed.append((mm.start(), end_idx))
    return symbols


def extract_frontend_symbols(content: str, container_name: str, is_store: bool = False) -> list[dict]:
    """Funciones/metodos con rango de lineas exacto a nivel de simbolo
    individual dentro de un archivo frontend -- FrontendSymbol (Fase 3, Site
    Knowledge Graph, 2026-08-10). `container_name` es el identificador del
    "dueno" logico del archivo (stem del componente/composable, o store_id
    para Pinia stores) -- se usa como class_name para que el simbolo quede
    CONTAINS por el nodo FrontendComponent/Composable/PiniaStore/FrontendView
    correspondiente via la misma logica de builder.py::_add_one_file() que
    ya usa Python (matching por nombre de nodo existente en el mismo path).

    Cubre (ver seccion de scope arriba del archivo para lo que se deja
    fuera): function declarations, const/let arrow functions con cuerpo de
    bloque, computed()/watch()/watchEffect() (asignados o sueltos),
    lifecycle hooks (onMounted/onUnmounted/...) sueltos, y -- solo si
    is_store=True -- metodos de `actions:`/`getters:` de un Pinia
    option-store.

    A proposito NO hay skip de matches anidados aca (a diferencia de
    _extract_store_block_methods): una funcion nombrada declarada DENTRO de
    otra (ej. `fetchTicket` dentro del cuerpo de un composable exportado
    `useOperationTracking`) es exactamente el patron real y util que este
    scanner debe capturar -- ver useOperationTracking.js real, donde TODA
    la logica vive anidada dentro de la funcion exportada. Cada patron
    exige su propia palabra clave/anclaje (function/const/let/on.../watch),
    mutuamente excluyentes entre si en la misma posicion de texto, asi que
    no hay riesgo de que dos pasadas distintas cuenten el mismo simbolo dos
    veces."""
    symbols: list[dict] = []

    for m in _FUNCTION_DECL_RE.finditer(content):
        brace_idx = m.end() - 1
        end_idx = _match_balanced(content, brace_idx, "{", "}")
        if end_idx is None:
            continue
        name = m.group(2)
        body = content[brace_idx:end_idx]
        symbols.append(_make_frontend_symbol(
            container_name, name, "function", body,
            _line_no(content, m.start(2)), _line_no(content, end_idx),
            is_async=bool(m.group(1)),
        ))

    for m in _ARROW_CONST_RE.finditer(content):
        brace_idx = m.end() - 1
        end_idx = _match_balanced(content, brace_idx, "{", "}")
        if end_idx is None:
            continue
        name = m.group(1)
        body = content[brace_idx:end_idx]
        symbols.append(_make_frontend_symbol(
            container_name, name, "function", body,
            _line_no(content, m.start(1)), _line_no(content, end_idx),
            is_async=bool(m.group(2)),
        ))

    for m in _HOOK_ASSIGN_RE.finditer(content):
        paren_idx = m.end() - 1
        end_idx = _match_balanced(content, paren_idx, "(", ")")
        if end_idx is None:
            continue
        name, hook = m.group(1), m.group(2)
        body = content[paren_idx:end_idx]
        symbols.append(_make_frontend_symbol(
            container_name, name, _REACTIVITY_HOOKS[hook], body,
            _line_no(content, m.start(1)), _line_no(content, end_idx),
        ))

    hook_counts: dict[str, int] = {}
    for m in _BARE_LIFECYCLE_RE.finditer(content):
        hook_name = m.group(1)
        if hook_name not in _LIFECYCLE_HOOKS:
            continue
        paren_idx = m.end() - 1
        end_idx = _match_balanced(content, paren_idx, "(", ")")
        if end_idx is None:
            continue
        hook_counts[hook_name] = hook_counts.get(hook_name, 0) + 1
        suffix = "" if hook_counts[hook_name] == 1 else f"_{hook_counts[hook_name]}"
        body = content[paren_idx:end_idx]
        symbols.append(_make_frontend_symbol(
            container_name, f"{hook_name}{suffix}", "lifecycle", body,
            _line_no(content, m.start(1)), _line_no(content, end_idx),
        ))

    watch_counts: dict[str, int] = {}
    for m in _BARE_WATCH_RE.finditer(content):
        hook_name = m.group(1)
        paren_idx = m.end() - 1
        end_idx = _match_balanced(content, paren_idx, "(", ")")
        if end_idx is None:
            continue
        watch_counts[hook_name] = watch_counts.get(hook_name, 0) + 1
        suffix = "" if watch_counts[hook_name] == 1 else f"_{watch_counts[hook_name]}"
        body = content[paren_idx:end_idx]
        symbols.append(_make_frontend_symbol(
            container_name, f"{hook_name}{suffix}", "watch", body,
            _line_no(content, m.start(1)), _line_no(content, end_idx),
        ))

    if is_store:
        symbols.extend(_extract_store_block_methods(content, "actions", "method", container_name))
        symbols.extend(_extract_store_block_methods(content, "getters", "computed", container_name))
    else:
        # Solo si no es un Pinia store (que ya cubre su propio caso arriba
        # y cuya declaracion `= defineStore(...)` de todos modos no matchea
        # este patron) -- objeto exportado plano tipo "custom API wrapper".
        symbols.extend(_extract_flat_exported_object_methods(content, container_name))

    return symbols
