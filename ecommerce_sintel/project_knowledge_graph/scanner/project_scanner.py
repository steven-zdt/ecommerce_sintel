"""
Orquestador de descubrimiento del proyecto -- recorre una app Django o el
arbol frontend y devuelve datos estructurados, usando python_scanner.py/
django_scanner.py/frontend_scanner.py como building blocks. Extraido de
ai_engine/auditor.py::ProjectAuditor.audit_app/audit_frontend_file/
audit_frontend (Fase 4, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH,
2026-08-08).

Responde: "¿que existe en el proyecto?" -- no "¿como esta relacionado?" (eso
es responsabilidad de knowledge_graph/, ver Fase 10 del plan).
"""
import ast
from collections import defaultdict
from pathlib import Path

from project_knowledge_graph.config import API_PREFIXES, BASE_DIR, FRONTEND_DIR
from project_knowledge_graph.scanner.django_scanner import (
    detect_python_role,
    extract_api_test_calls,
    extract_direct_symbol_calls,
    extract_model_fields,
    extract_model_manager_usages,
    extract_signal_registrations,
    extract_task_queue_calls,
    extract_url_patterns,
    extract_websocket_patterns,
    is_model_class,
    is_permission_class,
    is_serializer_class,
    is_task_function,
    is_test_class,
    is_viewset_class,
)
from project_knowledge_graph.scanner.frontend_scanner import (
    detect_vue_role,
    extract_frontend_symbols,
    extract_pinia_store,
    extract_router_routes,
    extract_use_hook_calls,
    extract_vue_api_calls,
    extract_vue_component_imports,
    extract_vue_emits_props,
    extract_vue_template_tags,
    isolate_vue_script,
)
from project_knowledge_graph.scanner.python_scanner import (
    extract_classes,
    extract_env_var_calls,
    extract_imports,
    extract_symbols,
    file_stats,
    read_source,
    safe_parse_text,
)


def scan_app(app_name: str, django_apps: list[str]) -> dict:
    """Escanea una app Django completa: modelos, serializers, viewsets,
    permisos, consumers, tasks, signals, comandos, selectors, services,
    url_patterns, migraciones, y cross_app_imports reales (no heuristica de
    nombre)."""
    app_dir = BASE_DIR / app_name
    if not app_dir.exists():
        return {}

    app_data = {
        "name": app_name,
        "api_prefix": API_PREFIXES.get(app_name, f"api/v1/{app_name}"),
        "models": [],
        "serializers": [],
        "viewsets": [],
        "permissions": [],
        "consumers": [],
        "tasks": [],
        "signals": [],
        "commands": [],
        "management_commands": [],
        "selectors": [],
        "services": [],
        "url_patterns": [],
        "websocket_patterns": [],
        "migrations": [],
        "files": [],
        "cross_app_imports": [],
    }

    for py_file in sorted(app_dir.rglob("*.py")):
        rel = str(py_file.relative_to(BASE_DIR))
        rel_fwd = rel.replace("\\", "/")

        if "__pycache__" in rel_fwd:
            continue

        role = detect_python_role(rel_fwd)
        source = read_source(py_file)
        file_entry = {
            "path": rel_fwd, "role": role, "classes": [], "functions": [],
            "language": "python", "symbols": [],
            **file_stats(source),
        }

        tree = safe_parse_text(source)
        if tree is None:
            app_data["files"].append(file_entry)
            continue

        classes = extract_classes(tree)
        file_entry["classes"] = [c["name"] for c in classes]
        file_entry["symbols"] = extract_symbols(tree)
        file_entry["env_vars"] = extract_env_var_calls(tree)
        # model_usages (Fase 5, Site Knowledge Graph, 2026-08-10): evidencia
        # real de que funcion/metodo lee o escribe que Model -- se escanea
        # en TODO archivo Python (no solo role=="selector"/"command"), un
        # Selector puede tener un helper de escritura y un ViewSet a veces
        # consulta directo sin pasar por la capa de Service.
        file_entry["model_usages"] = extract_model_manager_usages(tree)
        # task_queue_calls (Fase 6 "Execution Graph", 2026-08-10): evidencia
        # real de que funcion/metodo encola que Celery task -- ver
        # scanner/django_scanner.py::extract_task_queue_calls.
        file_entry["task_queue_calls"] = extract_task_queue_calls(tree)
        # is_test (Fase 7 "Test Graph", 2026-08-10): marca sobre cada Symbol
        # ya existente (sin node type nuevo, ver seccion de scope en
        # django_scanner.py) -- metodo de una clase TestCase-like, o
        # funcion de modulo `test_*` (convencion pytest, ej. este mismo
        # repo de tests). api_test_calls/direct_symbol_calls se escanean en
        # TODO archivo (no solo role=="test") por el mismo motivo que
        # model_usages arriba: costo marginal minimo, evita asumir que
        # "test" solo vive en archivos con ese role.
        test_class_names = {c["name"] for c in classes if is_test_class(c["bases"])}
        for sym in file_entry["symbols"]:
            is_module_test_fn = sym.get("class_name") is None and sym["name"].startswith("test_")
            sym["is_test"] = sym.get("class_name") in test_class_names or is_module_test_fn
        file_entry["api_test_calls"] = extract_api_test_calls(tree)
        file_entry["direct_symbol_calls"] = extract_direct_symbol_calls(tree)

        for imp in extract_imports(tree):
            target_app = imp.split(".")[0]
            if target_app in django_apps and target_app != app_name:
                app_data["cross_app_imports"].append({
                    "target_app": target_app,
                    "via_file": rel_fwd,
                    "import": imp,
                })

        for sig in extract_signal_registrations(tree):
            if not any(s["name"] == sig["name"] and s["file"] == rel_fwd
                       for s in app_data["signals"]):
                app_data["signals"].append({
                    "name": sig["name"], "file": rel_fwd, "trigger": sig["trigger"],
                    "sender": sig.get("sender"), "signal_name": sig.get("signal_name"),
                })

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entry = {"name": node.name}
                if is_task_function(node.name, node.decorator_list):
                    entry["is_task"] = True
                file_entry["functions"].append(entry)

        if role == "model":
            for cls in classes:
                if cls["name"].startswith("_") or cls["name"] == "Meta":
                    continue
                bases = cls["bases"]
                fk_fields = []
                for cnode in ast.walk(tree):
                    if isinstance(cnode, ast.ClassDef) and cnode.name == cls["name"]:
                        fk_fields = extract_model_fields(cnode)
                        break
                app_data["models"].append({
                    "name": cls["name"], "file": rel_fwd, "bases": bases,
                    "methods": cls["methods"], "fields": fk_fields,
                })

        elif role == "serializer":
            for cls in classes:
                if not is_serializer_class(cls["bases"]):
                    continue
                app_data["serializers"].append({
                    "name": cls["name"], "file": rel_fwd,
                    "bases": cls["bases"], "fields": cls["fields"],
                })

        elif role == "viewset":
            for cls in classes:
                if not is_viewset_class(cls["bases"]):
                    continue
                actions = [m for m in cls["methods"]
                           if not m.startswith("_") and m not in
                           ("get_queryset", "get_serializer_class",
                            "get_permissions", "perform_create",
                            "perform_update", "perform_destroy")]
                app_data["viewsets"].append({
                    "name": cls["name"], "file": rel_fwd,
                    "bases": cls["bases"], "actions": actions,
                })

        elif role == "permission":
            for cls in classes:
                if not is_permission_class(cls["bases"]):
                    continue
                app_data["permissions"].append({"name": cls["name"], "file": rel_fwd})

        elif role == "consumer":
            for cls in classes:
                app_data["consumers"].append({
                    "name": cls["name"], "file": rel_fwd,
                    "bases": cls["bases"], "methods": cls["methods"],
                })

        elif role == "task":
            for fn in file_entry["functions"]:
                if fn.get("is_task"):
                    app_data["tasks"].append({"name": fn["name"], "file": rel_fwd})
            for cls in classes:
                if any("Task" in b for b in cls["bases"]):
                    app_data["tasks"].append({"name": cls["name"], "file": rel_fwd, "type": "class"})

        elif role in ("service", "command", "selector", "pricing"):
            for cls in classes:
                app_data["services"].append({
                    "name": cls["name"], "file": rel_fwd, "role": role, "methods": cls["methods"],
                })
            for fn in file_entry["functions"]:
                if role == "selector":
                    app_data["selectors"].append({"name": fn["name"], "file": rel_fwd})
                elif role == "command":
                    app_data["commands"].append({"name": fn["name"], "file": rel_fwd})
                else:
                    app_data["services"].append({"name": fn["name"], "file": rel_fwd, "role": role})

        elif role == "management_cmd":
            app_data["management_commands"].append({"name": py_file.stem, "file": rel_fwd})

        elif role == "url":
            app_data["url_patterns"].extend(extract_url_patterns(tree))

        elif role == "routing":
            app_data["websocket_patterns"].extend(extract_websocket_patterns(tree))

        elif role == "migration":
            app_data["migrations"].append(py_file.stem)

        app_data["files"].append(file_entry)

    return app_data


_FRONTEND_LANGUAGE_BY_SUFFIX = {".vue": "vue", ".ts": "typescript", ".js": "javascript"}


def scan_frontend_file(path: Path) -> dict:
    rel = str(path.relative_to(FRONTEND_DIR)).replace("\\", "/")
    role = detect_vue_role(rel)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"path": rel, "role": role, "error": True}

    entry = {
        "path": rel, "role": role,
        "language": _FRONTEND_LANGUAGE_BY_SUFFIX.get(path.suffix, "unknown"),
        "api_calls": extract_vue_api_calls(content),
        # hook_calls (Fase 4, 2026-08-10) reemplaza store_imports [RETIRADO]:
        # nombre COMPLETO de cada hook use*(...) realmente llamado en el
        # archivo -- builder.py lo matchea EXACTO contra PiniaStore.hook_name
        # o Composable.name (ver frontend_scanner.py::extract_use_hook_calls
        # para el bug real que esto corrige: 0 aristas USES_STORE con la
        # logica anterior de substring).
        "hook_calls": extract_use_hook_calls(content),
        "component_imports": extract_vue_component_imports(content),
        **file_stats(content),
    }

    if path.suffix == ".vue":
        pe = extract_vue_emits_props(content)
        entry["props"] = pe["props"]
        entry["emits"] = pe["emits"]
        entry["template_tags"] = extract_vue_template_tags(content)

    store_info = None
    if role == "store":
        store_info = extract_pinia_store(content)
        if store_info:
            entry["store_info"] = store_info

    if role == "router":
        entry["routes"] = extract_router_routes(content)

    # FrontendSymbol (Fase 3, Site Knowledge Graph, 2026-08-10): container_name
    # debe coincidir con el .name que builder.py::_add_frontend_entities() le
    # da al nodo FrontendComponent/PiniaStore/Composable/FrontendView de este
    # mismo path -- para Pinia usa store_id (no siempre == stem del archivo),
    # para todo lo demas usa el stem, igual que builder.py.
    container_name = store_info["store_id"] if store_info else path.stem
    scan_text = isolate_vue_script(content) if path.suffix == ".vue" else content
    entry["symbols"] = extract_frontend_symbols(scan_text, container_name, is_store=(role == "store"))

    return entry


def scan_frontend() -> dict:
    if not FRONTEND_DIR.exists():
        return {}

    result = defaultdict(list)
    extensions = {".vue", ".js", ".ts"}

    for fpath in sorted(FRONTEND_DIR.rglob("*")):
        if fpath.suffix not in extensions:
            continue
        rel = str(fpath.relative_to(FRONTEND_DIR)).replace("\\", "/")
        if "node_modules" in rel or "__pycache__" in rel:
            continue
        if ".cache" in rel or "dist" in rel:
            continue

        entry = scan_frontend_file(fpath)
        role = entry["role"]

        if role == "view":
            result["views"].append(entry)
        elif role in ("component", "module_view"):
            result["components"].append(entry)
        elif role == "composable":
            result["composables"].append(entry)
        elif role == "store":
            result["stores"].append(entry)
        elif role == "router":
            result["router"].append(entry)
        elif role == "layout":
            result["layouts"].append(entry)
        else:
            result["misc"].append(entry)

    return dict(result)
