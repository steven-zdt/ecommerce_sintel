"""
Scanner generico de AST Python -- no sabe nada de Django, solo interpreta
sintaxis Python (clases, imports, valores string, funciones/metodos con rango
de lineas). Extraido de ai_engine/auditor.py (Fase 4, 2026-08-08); extendido
Fase 1 (Site Knowledge Graph, 2026-08-10) con extract_symbols() y file_stats()
para las entidades File/Symbol. Ver django_scanner.py para la interpretacion
especifica de Django (roles, modelos, viewsets).
"""
import ast
import hashlib
from pathlib import Path


def safe_parse(path: Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def read_source(path: Path) -> str:
    """Lee el archivo una sola vez -- usado por safe_parse_text()/file_stats()
    para no leer el mismo archivo dos veces (una para el AST, otra para hash/
    conteo de lineas)."""
    return path.read_text(encoding="utf-8", errors="replace")


def safe_parse_text(source: str):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def file_stats(source: str) -> dict:
    """Metadata de nivel File (Fase 1, Site Knowledge Graph): conteo de
    lineas y hash de contenido (mismo algoritmo que incremental/hashing.py,
    reimplementado aca a proposito -- scanner/ no debe depender de
    incremental/, son capas distintas)."""
    return {
        "lines": source.count("\n") + 1 if source else 0,
        "hash": hashlib.md5(source.encode("utf-8")).hexdigest(),
    }


def get_base_names(node: ast.ClassDef) -> list[str]:
    names = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            names.append(b.id)
        elif isinstance(b, ast.Attribute):
            names.append(f"{b.value.id}.{b.attr}" if isinstance(b.value, ast.Name) else b.attr)
    return names


def extract_string_value(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_classes(tree: ast.Module) -> list[dict]:
    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = get_base_names(node)
        methods = []
        fields = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.AsyncFunctionDef):
                methods.append(f"async {item.name}")
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                # Capture field assignments (model fields, serializer fields)
                targets = []
                if isinstance(item, ast.Assign):
                    for t in item.targets:
                        if isinstance(t, ast.Name):
                            targets.append(t.id)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    targets.append(item.target.id)
                for t in targets:
                    if not t.startswith("_"):
                        fields.append(t)
        classes.append({
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "fields": fields,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
        })
    return classes


_ENV_CALL_NAMES = {"config", "env"}  # python-decouple ('config') es el patron
# real confirmado de este proyecto (ver ecommerce/settings/base.py); 'env' se
# soporta tambien por si algun archivo usa django-environ en su lugar -- sin
# costo si no aparece.


def extract_env_var_calls(tree: ast.Module) -> list[str]:
    """Environment Contract (Fase 2, Site Knowledge Graph, 2026-08-10):
    nombres de variables de entorno leidas via config('VAR', ...)/env('VAR',
    ...) en cualquier archivo -- no solo settings.py, cualquier modulo puede
    leer una env var directo (ver ai_engine/config.py como ejemplo real).
    Deduplicado, orden estable."""
    names: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id in _ENV_CALL_NAMES):
            continue
        if not node.args:
            continue
        value = extract_string_value(node.args[0])
        if value and value not in seen:
            seen.add(value)
            names.append(value)
    return names


def extract_symbols(tree: ast.Module) -> list[dict]:
    """Funciones y metodos con rango de lineas exacto -- entidad Symbol
    (Fase 1, Site Knowledge Graph, 2026-08-10). Un Symbol por FunctionDef/
    AsyncFunctionDef, tanto a nivel de modulo (kind='function') como dentro
    de una clase (kind='method', con qualified_name 'Clase.metodo' igual al
    ejemplo del plan: 'AvailabilityEngine.calculate_availability'). No
    recorre funciones anidadas dentro de otra funcion -- esas no son
    unidades de cambio utiles para "que archivo/segmento tocar", solo
    ruido adicional."""
    symbols = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append({
                    "name": item.name,
                    "qualified_name": f"{node.name}.{item.name}",
                    "kind": "method",
                    "class_name": node.name,
                    "start_line": item.lineno,
                    "end_line": getattr(item, "end_lineno", item.lineno),
                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                })

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({
                "name": node.name,
                "qualified_name": node.name,
                "kind": "function",
                "class_name": None,
                "start_line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })

    return symbols


def extract_imports(tree: ast.Module) -> list[str]:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
    return imports
