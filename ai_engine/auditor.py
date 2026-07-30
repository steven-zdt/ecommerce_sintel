"""
auditor.py - Sintel Project Architect Auditor
Builds PROJECT_MAP.json: complete dependency graph of the entire project.
Usage: python ai_engine/auditor.py
Output: ai_engine/PROJECT_MAP.json
"""
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

def _resolve_base_dir() -> Path:
    """
    [CORREGIDO 2026-07-30, AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md §16] Corriendo desde
    el host, ecommerce_sintel/ es un directorio hermano real de ai_engine/ -- pero dentro
    del contenedor sintel_ai (docker-compose.yml) el mismo codigo se monta en
    /workspace (volumes: .:/workspace:ro), NO en /ecommerce_sintel -- confirmado
    encontrando BASE_DIR.exists() == False en vivo dentro del contenedor real al probar
    el endpoint /refresh extendido en esta misma auditoria. config.py ya resuelve esto
    correctamente para el resto del AI Core via CODEBASE_PATH (env var, override real en
    docker-compose.yml: "/workspace") -- este modulo no importaba config.py para no sumar
    una dependencia (python-decouple) a un script que hoy solo usa stdlib; se lee el env
    var directo en su lugar, con el mismo fallback de siempre para ejecucion desde host.
    """
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    return Path(__file__).resolve().parent.parent / "ecommerce_sintel"


BASE_DIR = _resolve_base_dir()
FRONTEND_DIR = BASE_DIR / "frontend" / "src"
OUTPUT_PATH = Path(__file__).resolve().parent / "PROJECT_MAP.json"

DJANGO_APPS = [
    "accounts", "cart", "core", "dashboard",
    "ecommerce", "inventory", "kyc", "marketing", "notifications",
    "operations", "organization", "orders", "payment", "quotes",
    "renting", "security", "shared", "shop", "support",
    "technical_services", "users",
]

# Role detection for Python files
ROLE_PATTERNS = [
    ("migration",      re.compile(r"migrations/\d+_")),
    ("management_cmd", re.compile(r"management/commands/(?!__init__)")),
    ("test",           re.compile(r"(^|/)tests?(/|\.py)")),
    ("consumer",       re.compile(r"consumers?\.py$")),
    ("task",           re.compile(r"tasks?\.py$")),
    ("signal",         re.compile(r"signals?\.py$")),
    ("middleware",     re.compile(r"middlewares?\.py$")),
    ("permission",     re.compile(r"permissions?\.py$")),
    ("serializer",     re.compile(r"serializers?\.py$")),
    ("viewset",        re.compile(r"(views?|viewsets?)\.py$")),
    ("url",            re.compile(r"urls?\.py$")),
    ("selector",       re.compile(r"selectors?\.py$")),
    ("command",        re.compile(r"commands?\.py$")),
    ("service",        re.compile(r"services?\.py$")),
    ("pricing",        re.compile(r"pricing.*\.py$")),
    ("model",          re.compile(r"models?\.py$")),
    ("admin",          re.compile(r"admin\.py$")),
    ("app_config",     re.compile(r"apps\.py$")),
    ("settings",       re.compile(r"settings.*\.py$")),
    ("routing",        re.compile(r"routing\.py$")),
    ("celery",         re.compile(r"celery\.py$")),
]

# Role detection for Vue/JS files
VUE_ROLE_PATTERNS = [
    ("store",       re.compile(r"store[s]?/.*\.(js|ts|vue)$")),
    ("composable",  re.compile(r"composable[s]?/use\w+\.(js|ts)$")),
    ("router",      re.compile(r"router.*\.(js|ts)$")),
    ("layout",      re.compile(r"(layouts?|Layout)\w*\.vue$")),
    ("view",        re.compile(r"views?/.*\.vue$")),
    ("component",   re.compile(r"components?/.*\.vue$")),
    ("module_view", re.compile(r"modules?/\w+/\w+\.vue$")),
    ("app_entry",   re.compile(r"(App|main)\.(js|ts|vue)$")),
]

# Known API base prefixes
API_PREFIXES = {
    "accounts":          "api/v1/auth",
    "users":             "api/v1/users",
    "dashboard":         "api/v1/dashboard",
    "shop":              "api/v1/shop",
    "cart":              "api/v1/cart",
    "orders":            "api/v1/orders",
    "payment":           "api/v1/payment",
    "inventory":         "api/v1/inventory",
    "technical_services": "api/v1/services",
    "quotes":            "api/v1/quotes",
    "marketing":         "api/v1/marketing",
    "renting":           "api/v1/renting",
    "core":              "api/v1/core",
    "notifications":     "api/v1/notifications",
    "operations":        "api/v1/operations",
    "support":           "api/v1/support",
    "shipping":          "api/v1/shipping",
    "kyc":               "api/v1/auth",
    "security":          "api/v1/security",
    "organization":      "api/v1/organization",
}

# ---------------------------------------------------------------------------
# PYTHON / AST HELPERS
# ---------------------------------------------------------------------------

def safe_parse(path: Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


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
        })
    return classes


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


def extract_url_patterns(tree: ast.Module) -> list[dict]:
    """Extract router.register() and path() calls from urls.py files."""
    patterns = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # router.register(r'prefix', ViewSet, basename='x')
        if (isinstance(func, ast.Attribute) and func.attr == "register"):
            args = node.args
            if len(args) >= 2:
                prefix = extract_string_value(args[0])
                viewset = args[1].id if isinstance(args[1], ast.Name) else str(args[1])
                basename = None
                for kw in node.keywords:
                    if kw.arg == "basename":
                        basename = extract_string_value(kw.value)
                if prefix:
                    patterns.append({"type": "router", "prefix": prefix.strip("^$"),
                                     "viewset": viewset, "basename": basename})
        # path('prefix/', include('app.urls'))
        elif (isinstance(func, ast.Name) and func.id == "path") or \
             (isinstance(func, ast.Attribute) and func.attr == "path"):
            args = node.args
            if len(args) >= 2:
                route = extract_string_value(args[0])
                if route:
                    patterns.append({"type": "path", "route": route})
    return patterns


def extract_model_fields(cls_node: ast.ClassDef) -> list[dict]:
    """Extract Django model field definitions with FK relations."""
    result = []
    for item in cls_node.body:
        if not isinstance(item, ast.Assign):
            continue
        for target in item.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            value = item.value
            if not isinstance(value, ast.Call):
                continue
            func = value.func
            field_type = ""
            if isinstance(func, ast.Attribute):
                field_type = func.attr
            elif isinstance(func, ast.Name):
                field_type = func.id
            # Capture FK/M2M related model
            related_model = None
            if field_type in ("ForeignKey", "OneToOneField", "ManyToManyField",
                              "GenericRelatedObjectManager"):
                if value.args:
                    first = value.args[0]
                    if isinstance(first, ast.Constant):
                        related_model = first.value
                    elif isinstance(first, ast.Name):
                        related_model = first.id
                    elif isinstance(first, ast.Attribute):
                        related_model = f"{first.value.id}.{first.attr}" if isinstance(first.value, ast.Name) else first.attr
            if not name.startswith("_"):
                result.append({
                    "name": name,
                    "field_type": field_type,
                    "related_model": related_model,
                })
    return result


def detect_python_role(rel_path: str) -> str:
    for role, pattern in ROLE_PATTERNS:
        if pattern.search(rel_path.replace("\\", "/")):
            return role
    return "misc"


def is_model_class(bases: list[str]) -> bool:
    model_bases = {"Model", "SintelBaseModel", "AbstractBaseUser",
                   "AbstractUser", "PolymorphicModel"}
    return any(b in model_bases or b.endswith("Model") for b in bases)


def is_viewset_class(bases: list[str]) -> bool:
    viewset_bases = {"ViewSet", "ModelViewSet", "ReadOnlyModelViewSet",
                     "GenericViewSet", "CreateModelMixin", "APIView",
                     "ListAPIView", "RetrieveAPIView", "CreateAPIView",
                     "UpdateAPIView", "DestroyAPIView", "ListCreateAPIView",
                     "RetrieveUpdateDestroyAPIView", "RetrieveUpdateAPIView"}
    return any(b in viewset_bases or "ViewSet" in b or "APIView" in b
               for b in bases)


def is_serializer_class(bases: list[str]) -> bool:
    return any("Serializer" in b for b in bases)


def is_permission_class(bases: list[str]) -> bool:
    return any("Permission" in b or "BasePermission" in b for b in bases)


def extract_signal_registrations(tree: ast.Module) -> list[dict]:
    """Fase 3: deteccion real de signals -- NO depende de que el archivo se
    llame signals.py (limitacion conocida documentada en
    AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md §15.3, ej. el signal de
    TechnicianProfile vive inline en accounts/models.py). Detecta:
      1. @receiver(...) sobre una funcion, en cualquier archivo.
      2. alguna_señal.connect(handler, ...) como llamada, en cualquier archivo.
    """
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                dec_func = dec.func if isinstance(dec, ast.Call) else dec
                fname = None
                if isinstance(dec_func, ast.Name):
                    fname = dec_func.id
                elif isinstance(dec_func, ast.Attribute):
                    fname = dec_func.attr
                if fname == "receiver":
                    found.append({"name": node.name, "trigger": "receiver_decorator"})
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "connect" and node.args:
                first = node.args[0]
                handler_name = (first.id if isinstance(first, ast.Name) else
                                 first.attr if isinstance(first, ast.Attribute) else
                                 "connect_call")
                found.append({"name": handler_name, "trigger": "connect_call"})
    return found


def is_task_function(name: str, decorators) -> bool:
    for d in decorators:
        if isinstance(d, ast.Name) and d.id in ("shared_task", "task"):
            return True
        if isinstance(d, ast.Attribute) and d.attr in ("task", "shared_task"):
            return True
        if isinstance(d, ast.Call):
            func = d.func
            if isinstance(func, ast.Attribute) and func.attr in ("task", "shared_task"):
                return True
    return False


# ---------------------------------------------------------------------------
# VUE / JS HELPERS
# ---------------------------------------------------------------------------

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
    """Extract api.get/post/patch/delete/put calls and their URL patterns."""
    calls = []
    # Match: api.get('/api/v1/...'), api.post(`/api/v1/...`), etc.
    patterns = [
        re.compile(r'api\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]'),
        re.compile(r'axios\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]'),
        re.compile(r'(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+api[^`\'"]+)[`\'"]'),
    ]
    for pat in patterns:
        for m in pat.finditer(content):
            method, url = m.group(1).upper(), m.group(2)
            calls.append({"method": method, "url": url})
    return calls


def extract_vue_store_imports(content: str) -> list[str]:
    stores = []
    patterns = [
        re.compile(r'use(\w+Store)\s*\(\s*\)'),
        re.compile(r'import\s+\{[^}]*\}\s+from\s+[\'"]([^\'"]*/store[^\'"]*)'),
        re.compile(r"useStore\(\)"),
    ]
    for pat in patterns:
        for m in pat.finditer(content):
            stores.append(m.group(1) if m.lastindex and m.group(1) else m.group(0))
    return list(set(stores))


def extract_vue_component_imports(content: str) -> list[str]:
    components = []
    pat = re.compile(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+\.vue)['\"]")
    for m in pat.finditer(content):
        components.append(m.group(1))
    return list(set(components))


def extract_vue_template_tags(content: str) -> list[str]:
    """Fase 3/4 (AUDITORIA/14): tags de componente usados en el <template>,
    PascalCase o kebab-case -- necesario porque este proyecto usa auto-import
    de componentes (confirmado: BaseAccordion/BaseReviews se usan en
    PublicDetailView.vue sin ningun 'import' explicito). Sin esto, todo
    componente auto-importado aparece como "codigo muerto" por error."""
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


def extract_pinia_store(content: str) -> dict | None:
    id_match = re.search(r"defineStore\s*\(\s*['\"](\w+)['\"]", content)
    state_match = re.search(r"state:\s*\(\s*\)\s*=>\s*\(\s*\{([^}]+)\}", content, re.DOTALL)
    actions = re.findall(r"async\s+(\w+)\s*\(|^\s+(\w+)\s*\([^)]*\)\s*\{", content, re.MULTILINE)
    if not id_match:
        return None
    return {
        "store_id": id_match.group(1),
        "state_keys": [m.group(1) for m in re.finditer(r"(\w+)\s*:", state_match.group(1))] if state_match else [],
        "actions": [a[0] or a[1] for a in actions if a[0] or a[1]],
    }


def extract_router_routes(content: str) -> list[dict]:
    routes = []
    # Match path: '/some/path', component: SomeView
    for m in re.finditer(
        r"path\s*:\s*['\"]([^'\"]+)['\"].*?(?:name\s*:\s*['\"](\w+)['\"])?.*?(?:component\s*:\s*(\w+))?",
        content, re.DOTALL
    ):
        path, name, comp = m.group(1), m.group(2), m.group(3)
        routes.append({"path": path, "name": name, "component": comp})
    return routes


# ---------------------------------------------------------------------------
# AUDITOR CORE
# ---------------------------------------------------------------------------

class ProjectAuditor:
    def __init__(self):
        self.project_map: dict[str, Any] = {
            "meta": {
                "generated_at": "",
                "base_dir": str(BASE_DIR),
                "apps": [],
                "frontend_dir": str(FRONTEND_DIR),
            },
            "apps": {},
            "frontend": {
                "views": [],
                "components": [],
                "composables": [],
                "stores": [],
                "router": [],
                "layouts": [],
                "modules": [],
            },
            "endpoints": [],
            "cross_refs": {
                "endpoint_to_viewset": {},
                "viewset_to_serializer": {},
                "model_to_viewset": {},
                "frontend_to_endpoint": {},
                "store_to_endpoint": {},
            },
        }

    # ------------------------------------------------------------------ #
    # DJANGO APP AUDIT
    # ------------------------------------------------------------------ #

    def audit_app(self, app_name: str) -> dict:
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
            "migrations": [],
            "files": [],
            "cross_app_imports": [],
        }

        for py_file in sorted(app_dir.rglob("*.py")):
            rel = str(py_file.relative_to(BASE_DIR))
            rel_fwd = rel.replace("\\", "/")

            # Skip pycache
            if "__pycache__" in rel_fwd:
                continue

            role = detect_python_role(rel_fwd)
            file_entry = {
                "path": rel_fwd,
                "role": role,
                "classes": [],
                "functions": [],
            }

            tree = safe_parse(py_file)
            if tree is None:
                app_data["files"].append(file_entry)
                continue

            classes = extract_classes(tree)
            file_entry["classes"] = [c["name"] for c in classes]

            # Fase 3 (AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md) -- IMPORTS real,
            # no heuristica de nombre: cualquier import cuyo primer segmento sea
            # otra app Django conocida es acoplamiento cross-app real, verificable.
            for imp in extract_imports(tree):
                target_app = imp.split(".")[0]
                if target_app in DJANGO_APPS and target_app != app_name:
                    app_data["cross_app_imports"].append({
                        "target_app": target_app,
                        "via_file": rel_fwd,
                        "import": imp,
                    })

            # Signals: deteccion universal (cualquier archivo), no solo signals.py
            for sig in extract_signal_registrations(tree):
                if not any(s["name"] == sig["name"] and s["file"] == rel_fwd
                           for s in app_data["signals"]):
                    app_data["signals"].append({
                        "name": sig["name"], "file": rel_fwd, "trigger": sig["trigger"],
                    })

            # Top-level functions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only direct module-level functions
                    pass
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    entry = {"name": node.name}
                    if is_task_function(node.name, node.decorator_list):
                        entry["is_task"] = True
                    file_entry["functions"].append(entry)

            # Classify by role
            if role == "model":
                for cls in classes:
                    if cls["name"].startswith("_") or cls["name"] == "Meta":
                        continue
                    bases = cls["bases"]
                    if not is_model_class(bases) and not any(
                        b in bases for b in ("BaseModel", "SintelBaseModel")
                    ):
                        # Still capture if name looks like a model
                        pass
                    # Re-parse to get field details
                    model_tree = safe_parse(py_file)
                    fk_fields = []
                    if model_tree:
                        for cnode in ast.walk(model_tree):
                            if isinstance(cnode, ast.ClassDef) and cnode.name == cls["name"]:
                                fk_fields = extract_model_fields(cnode)
                                break
                    app_data["models"].append({
                        "name": cls["name"],
                        "file": rel_fwd,
                        "bases": bases,
                        "methods": cls["methods"],
                        "fields": fk_fields,
                    })

            elif role == "serializer":
                for cls in classes:
                    if not is_serializer_class(cls["bases"]):
                        continue
                    app_data["serializers"].append({
                        "name": cls["name"],
                        "file": rel_fwd,
                        "bases": cls["bases"],
                        "fields": cls["fields"],
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
                        "name": cls["name"],
                        "file": rel_fwd,
                        "bases": cls["bases"],
                        "actions": actions,
                    })

            elif role == "permission":
                for cls in classes:
                    if not is_permission_class(cls["bases"]):
                        continue
                    app_data["permissions"].append({
                        "name": cls["name"],
                        "file": rel_fwd,
                    })

            elif role == "consumer":
                for cls in classes:
                    app_data["consumers"].append({
                        "name": cls["name"],
                        "file": rel_fwd,
                        "bases": cls["bases"],
                        "methods": cls["methods"],
                    })

            elif role == "task":
                for fn in file_entry["functions"]:
                    if fn.get("is_task"):
                        app_data["tasks"].append({
                            "name": fn["name"],
                            "file": rel_fwd,
                        })
                # Also check class-based tasks
                for cls in classes:
                    if any("Task" in b for b in cls["bases"]):
                        app_data["tasks"].append({
                            "name": cls["name"],
                            "file": rel_fwd,
                            "type": "class",
                        })

            elif role in ("service", "command", "selector", "pricing"):
                for cls in classes:
                    app_data["services"].append({
                        "name": cls["name"],
                        "file": rel_fwd,
                        "role": role,
                        "methods": cls["methods"],
                    })
                for fn in file_entry["functions"]:
                    if role == "selector":
                        app_data["selectors"].append({"name": fn["name"], "file": rel_fwd})
                    elif role == "command":
                        app_data["commands"].append({"name": fn["name"], "file": rel_fwd})
                    else:
                        app_data["services"].append({"name": fn["name"], "file": rel_fwd, "role": role})

            elif role == "management_cmd":
                app_data["management_commands"].append({
                    "name": py_file.stem,
                    "file": rel_fwd,
                })

            elif role == "url":
                tree2 = safe_parse(py_file)
                if tree2:
                    patterns = extract_url_patterns(tree2)
                    app_data["url_patterns"].extend(patterns)

            elif role == "migration":
                app_data["migrations"].append(py_file.stem)

            app_data["files"].append(file_entry)

        return app_data

    # ------------------------------------------------------------------ #
    # FRONTEND AUDIT
    # ------------------------------------------------------------------ #

    def audit_frontend_file(self, path: Path) -> dict:
        rel = str(path.relative_to(FRONTEND_DIR)).replace("\\", "/")
        role = detect_vue_role(rel)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return {"path": rel, "role": role, "error": True}

        entry = {
            "path": rel,
            "role": role,
            "api_calls": [],
            "store_imports": [],
            "component_imports": [],
        }

        entry["api_calls"] = extract_vue_api_calls(content)
        entry["store_imports"] = extract_vue_store_imports(content)
        entry["component_imports"] = extract_vue_component_imports(content)

        if path.suffix == ".vue":
            pe = extract_vue_emits_props(content)
            entry["props"] = pe["props"]
            entry["emits"] = pe["emits"]
            entry["template_tags"] = extract_vue_template_tags(content)

        if role == "store":
            store_info = extract_pinia_store(content)
            if store_info:
                entry["store_info"] = store_info

        if role == "router":
            entry["routes"] = extract_router_routes(content)

        return entry

    def audit_frontend(self) -> dict:
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

            entry = self.audit_frontend_file(fpath)
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

    # ------------------------------------------------------------------ #
    # CROSS-REFERENCE BUILDER
    # ------------------------------------------------------------------ #

    def build_cross_refs(self):
        cross = self.project_map["cross_refs"]

        # endpoint_to_viewset: from url_patterns
        for app_name, app_data in self.project_map["apps"].items():
            prefix = app_data.get("api_prefix", f"api/v1/{app_name}")
            for pat in app_data.get("url_patterns", []):
                if pat["type"] == "router":
                    endpoint = f"{prefix}/{pat['prefix']}"
                    vs = pat.get("viewset", "")
                    cross["endpoint_to_viewset"][endpoint] = {
                        "viewset": vs,
                        "app": app_name,
                        "basename": pat.get("basename"),
                    }

        # model_to_viewset: match serializer.Meta.model → viewset queryset
        for app_name, app_data in self.project_map["apps"].items():
            for vs in app_data.get("viewsets", []):
                # Heuristic: ProductViewSet → Product model
                vs_name = vs["name"]
                for suffix in ("ViewSet", "APIView", "View"):
                    if vs_name.endswith(suffix):
                        model_name = vs_name[:-len(suffix)]
                        for m in app_data.get("models", []):
                            if m["name"] == model_name:
                                cross["model_to_viewset"].setdefault(
                                    f"{app_name}.{model_name}", []
                                ).append(f"{app_name}.{vs_name}")

        # frontend_to_endpoint: from Vue api_calls
        fe = self.project_map.get("frontend", {})
        for group in ("views", "components", "composables", "stores", "misc"):
            for entry in fe.get(group, []):
                calls = entry.get("api_calls", [])
                if calls:
                    cross["frontend_to_endpoint"][entry["path"]] = [
                        {"method": c["method"], "url": c["url"]} for c in calls
                    ]

        # store_to_endpoint
        for store in fe.get("stores", []):
            calls = store.get("api_calls", [])
            if calls:
                store_id = store.get("store_info", {}).get("store_id", store["path"])
                cross["store_to_endpoint"][store_id] = calls

    # ------------------------------------------------------------------ #
    # ENDPOINTS FLAT LIST
    # ------------------------------------------------------------------ #

    def build_endpoints_list(self):
        endpoints = []
        cross = self.project_map["cross_refs"]
        for endpoint, info in cross["endpoint_to_viewset"].items():
            app_name = info["app"]
            app_data = self.project_map["apps"].get(app_name, {})
            vs_name = info["viewset"]
            vs_data = next((v for v in app_data.get("viewsets", []) if v["name"] == vs_name), {})
            endpoints.append({
                "endpoint": endpoint,
                "app": app_name,
                "viewset": vs_name,
                "actions": vs_data.get("actions", []),
                "basename": info.get("basename"),
                "http_methods": self._infer_http_methods(vs_data.get("bases", [])),
            })
        self.project_map["endpoints"] = endpoints

    def _infer_http_methods(self, bases: list[str]) -> list[str]:
        methods = []
        if any("ModelViewSet" in b for b in bases):
            methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        elif any("ReadOnly" in b for b in bases):
            methods = ["GET"]
        elif any("Create" in b for b in bases):
            methods.append("POST")
        elif any("List" in b for b in bases):
            methods.append("GET")
        elif any("Retrieve" in b for b in bases):
            methods.append("GET")
        elif any("Update" in b for b in bases):
            methods += ["PUT", "PATCH"]
        elif any("Destroy" in b for b in bases):
            methods.append("DELETE")
        elif any("APIView" in b for b in bases):
            methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        return methods or ["GET"]

    # ------------------------------------------------------------------ #
    # MAIN RUN
    # ------------------------------------------------------------------ #

    def run(self):
        import datetime
        self.project_map["meta"]["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

        print("Auditing Django apps...")
        for app_name in DJANGO_APPS:
            print(f"  [{app_name}]", end=" ", flush=True)
            app_data = self.audit_app(app_name)
            if app_data:
                self.project_map["apps"][app_name] = app_data
                self.project_map["meta"]["apps"].append(app_name)
                m_count = len(app_data.get("models", []))
                vs_count = len(app_data.get("viewsets", []))
                ep_count = len(app_data.get("url_patterns", []))
                print(f"models={m_count} viewsets={vs_count} endpoints={ep_count}")
            else:
                print("(not found)")

        print("\nAuditing frontend...")
        fe_data = self.audit_frontend()
        self.project_map["frontend"] = fe_data
        for k, v in fe_data.items():
            print(f"  {k}: {len(v)} files")

        print("\nBuilding cross-references...")
        self.build_cross_refs()
        self.build_endpoints_list()

        print(f"\nWriting {OUTPUT_PATH}...")
        OUTPUT_PATH.write_text(
            json.dumps(self.project_map, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        total_models = sum(len(a.get("models", [])) for a in self.project_map["apps"].values())
        total_viewsets = sum(len(a.get("viewsets", [])) for a in self.project_map["apps"].values())
        total_endpoints = len(self.project_map["endpoints"])
        total_fe = sum(len(v) for v in self.project_map["frontend"].values())
        total_cross = sum(len(v) for v in self.project_map["cross_refs"].values() if isinstance(v, dict))

        print("\n=== SUMMARY ===")
        print(f"  Apps audited:        {len(self.project_map['apps'])}")
        print(f"  Total models:        {total_models}")
        print(f"  Total viewsets:      {total_viewsets}")
        print(f"  Total endpoints:     {total_endpoints}")
        print(f"  Frontend files:      {total_fe}")
        print(f"  Cross-refs entries:  {total_cross}")
        print(f"\nPROJECT_MAP.json written to: {OUTPUT_PATH}")
        print(f"Size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")

        # Phase 4 — Knowledge Graph
        print("\nBuilding Knowledge Graph...")
        try:
            from knowledge_graph import build_and_save_knowledge_graph
            kg = build_and_save_knowledge_graph()
            print(f"  Nodes: {len(kg.nodes)}  Edges: {len(kg.edges)}")
        except Exception as exc:
            print(f"  WARNING: Knowledge Graph error: {exc}")

        # Phase 8 — Dependency Graph
        print("Building Dependency Graph...")
        try:
            from dependency_graph import save_dependency_graph
            dg = save_dependency_graph()
            print(f"  model_dependents: {len(dg.get('model_dependents', {}))}"
                  f"  endpoint_consumers: {len(dg.get('endpoint_consumers', {}))}")
        except Exception as exc:
            print(f"  WARNING: Dependency Graph error: {exc}")

        # Phase 9 & 10 — App + Global Memory
        print("Building Memory...")
        try:
            from memory_builder import build_all_memories
            mems = build_all_memories()
            print(f"  Per-app memories: {len(mems)}  Global: GLOBAL_MEMORY.json")
        except Exception as exc:
            print(f"  WARNING: Memory error: {exc}")

        # Phase 12 — AI Manifests per app
        print("Building AI Manifests...")
        try:
            from ai_manifest import build_all_manifests
            mfts = build_all_manifests()
            print(f"  AI_MANIFESTS: {len(mfts)} files + MASTER_MANIFEST.json")
        except Exception as exc:
            print(f"  WARNING: AI Manifest error: {exc}")

        # Fase 4 (AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md) — Graph Validator
        print("Running graph validations...")
        try:
            from graph_validator import run_all_validations, REPORT_PATH as _VREPORT
            vresult = run_all_validations()
            _VREPORT.write_text(json.dumps(vresult, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  {vresult['summary']}")
        except Exception as exc:
            print(f"  WARNING: Graph Validator error: {exc}")

        # Fase 5 — Graph Visualizer (HTML estatico, sin infra nueva)
        print("Building static graph visualization...")
        try:
            from graph_visualizer import build_html, OUT_PATH as _VIZPATH
            _VIZPATH.write_text(build_html(), encoding="utf-8")
            print(f"  {_VIZPATH.name}: {_VIZPATH.stat().st_size / 1024:.1f} KB")
        except Exception as exc:
            print(f"  WARNING: Graph Visualizer error: {exc}")

        # Phase 11 — Initialize file hash tracking
        print("Initializing incremental hash tracker...")
        try:
            from incremental_updater import _detect_via_hashes, _save_hash_db, _collect_app_files, _collect_frontend_files, _hash_file, HASH_DB_PATH, DJANGO_APPS as _DA, BASE_DIR as _BD
            import hashlib
            new_db: dict = {}
            for app_name in _DA:
                for path in _collect_app_files(app_name):
                    new_db[str(path)] = _hash_file(path)
            for path in _collect_frontend_files():
                new_db[str(path)] = _hash_file(path)
            _save_hash_db(new_db)
            print(f"  Hash DB initialized: {len(new_db)} files tracked at {HASH_DB_PATH.name}")
        except Exception as exc:
            print(f"  WARNING: Hash tracker error: {exc}")

        print("\nAll artifacts generated successfully.")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    auditor = ProjectAuditor()
    auditor.run()
