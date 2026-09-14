"""
Prueba de contrato arquitectonico: ai_engine NUNCA debe importar
project_knowledge_graph. FASE 0, 2026-08-10 -- separacion Site Knowledge
Graph / AI Editor Runtime ("AI Engine no conoce ni importa project_
knowledge_graph"; "project_knowledge_graph no conoce ni depende de ai_engine").

Reemplaza a test_pkg_compat_shims.py (retirado), que verificaba lo contrario
(que los imports SI existieran) -- esa era la arquitectura de Fase 17-18,
ya superada.
"""
from pathlib import Path

import pytest

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent


def test_no_ai_engine_source_file_imports_project_knowledge_graph():
    """Grep-equivalente en Python puro: ningun archivo .py de ai_engine (fuera
    de tests/) puede contener un import real de project_knowledge_graph.
    Menciones en comentarios/docstrings (ej. explicando por que YA NO se
    importa) son legitimas y no cuentan."""
    import ast

    offenders = []
    for py_file in AI_ENGINE_ROOT.rglob("*.py"):
        if "tests" in py_file.relative_to(AI_ENGINE_ROOT).parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] == "project_knowledge_graph" for alias in node.names):
                    offenders.append(str(py_file.relative_to(AI_ENGINE_ROOT)))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] == "project_knowledge_graph":
                    offenders.append(str(py_file.relative_to(AI_ENGINE_ROOT)))

    assert not offenders, (
        f"Estos archivos de ai_engine importan project_knowledge_graph, violando la regla "
        f"'AI Engine no conoce ni importa project_knowledge_graph': {offenders}"
    )


def test_ai_engine_core_modules_import_without_project_knowledge_graph_on_sys_path():
    """Verificacion literal de 'ai_engine puede ejecutarse sin project_
    knowledge_graph': fuerza que el paquete no sea importable (lo saca de
    sys.modules y bloquea su resolucion) y confirma que los modulos que antes
    dependian de el siguen importando limpio."""
    import sys

    sys.path = [p for p in sys.path if "project_knowledge_graph" not in p]
    for mod_name in list(sys.modules):
        if mod_name == "project_knowledge_graph" or mod_name.startswith("project_knowledge_graph."):
            del sys.modules[mod_name]

    import importlib

    for mod_name in ("planner", "graph", "incremental_updater"):
        try:
            importlib.import_module(mod_name)
        except ModuleNotFoundError as exc:
            if "project_knowledge_graph" in str(exc):
                pytest.fail(f"{mod_name}.py todavia depende de project_knowledge_graph: {exc}")
            # Dependencia de terceros ausente en este entorno (ej. langgraph
            # solo instalado dentro del contenedor sintel_ai, ver conftest.py)
            # -- no es lo que esta prueba verifica, se saltea en vez de fallar.
            pytest.skip(f"{mod_name}.py requiere una dependencia no instalada aca: {exc}")
