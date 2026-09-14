"""
Configuracion y constantes de project_knowledge_graph.

Extraido de ai_engine/auditor.py (Fase 4, PLAN_MAESTRO_DE_SEPARACION_PROJECT_
KNOWLEDGE_GRAPH, 2026-08-08). BASE_DIR usa la misma resolucion que el auditor
original -- via CODEBASE_PATH si esta seteado (Docker), o relativo al checkout
del host como fallback. Este modulo es standalone (sin python-decouple) a
proposito, igual que el original: el grafo estructural no debe depender de la
config de ai_engine.
"""
import os
import re
from pathlib import Path


def _resolve_base_dir() -> Path:
    """
    Corriendo desde el host, ecommerce_sintel/ es el directorio del proyecto
    Django+Vue. Dentro de un contenedor (ver docker-compose.yml de ai_engine,
    volumes: .:/workspace:ro) el mismo codigo se monta en otra ruta -- por eso
    se prioriza CODEBASE_PATH (env var) si esta seteado y existe, y solo se cae
    al calculo relativo por __file__ como fallback para ejecucion directa desde
    el host. Ver Regla 13 del plan: debe fallar EXPLICITO si el codigo fuente
    no esta disponible, no reportar 0 apps/modelos en silencio.
    """
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    return Path(__file__).resolve().parent.parent


BASE_DIR = _resolve_base_dir()
FRONTEND_DIR = BASE_DIR / "frontend" / "src"

if not BASE_DIR.exists():
    raise RuntimeError(
        f"project_knowledge_graph: BASE_DIR no existe ({BASE_DIR}). "
        "El codigo fuente del proyecto (ecommerce_sintel/) no esta disponible "
        "en este entorno -- corregir CODEBASE_PATH antes de auditar. "
        "(Regla 13 del plan de separacion: fallar explicito, nunca en silencio.)"
    )

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PROJECT_MAP_PATH = DATA_DIR / "PROJECT_MAP.json"
KNOWLEDGE_GRAPH_PATH = DATA_DIR / "KNOWLEDGE_GRAPH.json"
DEPENDENCY_GRAPH_PATH = DATA_DIR / "DEPENDENCY_GRAPH.json"
SNAPSHOT_META_PATH = DATA_DIR / "SNAPSHOT_META.json"
VALIDATION_REPORT_PATH = DATA_DIR / "GRAPH_VALIDATION_REPORT.json"
GRAPH_VIEW_PATH = DATA_DIR / "GRAPH_VIEW.html"
HASH_DB_PATH = DATA_DIR / ".file_hashes.json"
QUERY_AUDIT_LOG_PATH = DATA_DIR / "QUERY_AUDIT_LOG.jsonl"

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
    ("router",      re.compile(r"(router|\.routes)\.(js|ts)$")),
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
