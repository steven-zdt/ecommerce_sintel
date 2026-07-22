"""
project_map.py - Sintel Project Map Query Interface

Loads PROJECT_MAP.json and provides query functions for the AI Engine
to understand cross-app dependencies, impacted components, and endpoint chains.
"""
import json
import logging
import re
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

MAP_PATH = Path(__file__).resolve().parent / "PROJECT_MAP.json"


@lru_cache(maxsize=1)
def _load_map() -> dict:
    if not MAP_PATH.exists():
        logger.warning("[project_map] PROJECT_MAP.json not found at %s", MAP_PATH)
        return {}
    try:
        data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        logger.info("[project_map] Loaded PROJECT_MAP.json (%d apps, %d endpoints)",
                    len(data.get("apps", {})), len(data.get("endpoints", [])))
        return data
    except Exception as exc:
        logger.error("[project_map] Failed to load: %s", exc)
        return {}


def get_map() -> dict:
    return _load_map()


# ---------------------------------------------------------------------------
# IMPACT ANALYSIS
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "shop":               ["producto", "product", "variante", "variant", "precio", "price",
                           "brand", "marca", "categoria", "category", "descuento", "discount",
                           "oferta", "tax", "impuesto"],
    "orders":             ["orden", "order", "pedido", "checkout", "orderitem", "coupon",
                           "cupon", "shippingaddress", "create_from_cart"],
    "cart":               ["carrito", "cart", "cartitem"],
    "payment":            ["pago", "payment", "wompi", "webhook", "nequi", "cod", "tarjeta",
                           "transaction", "tokenizedcard", "pasarela"],
    "inventory":          ["inventario", "inventory", "stock", "kardex", "entrada", "salida",
                           "stockrecord", "bodega"],
    "technical_services": ["servicio", "service", "tecnico", "cotizacion", "quotation",
                           "servicebooking", "servicevariant", "tecnico"],
    "renting":            ["renta", "alquiler", "equipo", "equipment", "wizard",
                           "rentalrequest", "rentalperiod"],
    "notifications":      ["notificacion", "notification", "whatsapp", "email",
                           "dispatch_notification", "sms", "alerta"],
    "accounts":           ["perfil", "profile", "userprofile", "user_type", "customer",
                           "technician", "tecnico", "cuenta"],
    "users":              ["usuario", "user", "permiso", "permission", "admin", "staff",
                           "superuser", "autenticacion", "auth"],
    "marketing":          ["marketing", "campaign", "campana", "promocion", "descuento",
                           "coupon", "cupon", "oferta"],
    "dashboard":          ["dashboard", "bff", "panel", "admin", "orchestrator"],
    "quotes":             ["cotizacion", "quote", "presupuesto"],
    "support":            ["soporte", "support", "chat", "chatroom", "chatmessage"],
    "core":               ["home", "feed", "homeconfig", "portada", "inicio", "footer", "pie de pagina",
                           "brandslider", "marcas", "slider", "navbar", "footercta"],
    "operations":         ["operacion", "operation", "cronograma", "schedule", "agenda"],
    "shipping":           ["envio", "shipping", "domicilio", "entrega", "delivery"],
    "organization":       ["organizacion", "organization", "empresa", "company", "marca institucional",
                           "branding", "contacto", "contactinfo", "redes sociales", "sociallink", "seo"],
}


def find_affected_apps(task: str) -> list[str]:
    """
    Combines domain keyword matching + structural AST data from PROJECT_MAP.json.
    Returns apps sorted by relevance score.
    """
    pmap = get_map()
    apps_data = pmap.get("apps", {})
    task_lower = task.lower()
    scores: dict[str, int] = {}

    # Domain keyword pass
    for app_name, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in task_lower:
                scores[app_name] = scores.get(app_name, 0) + 2

    # Structural pass: match model/viewset/command names from project map
    for app_name, app_data in apps_data.items():
        # Model names
        for m in app_data.get("models", []):
            name = m["name"].lower()
            if len(name) > 3 and name in task_lower:
                scores[app_name] = scores.get(app_name, 0) + 3
        # Viewset name (strip suffix)
        for vs in app_data.get("viewsets", []):
            name = vs["name"].lower()
            for suffix in ("viewset", "apiview", "view"):
                name = name.replace(suffix, "")
            if len(name) > 3 and name in task_lower:
                scores[app_name] = scores.get(app_name, 0) + 2
        # App name itself
        if app_name.replace("_", " ") in task_lower or app_name in task_lower:
            scores[app_name] = scores.get(app_name, 0) + 2
        # URL prefix last segment
        prefix = app_data.get("api_prefix", "").lower().split("/")[-1]
        if len(prefix) > 3 and prefix in task_lower:
            scores[app_name] = scores.get(app_name, 0) + 1

    sorted_apps = sorted(scores, key=lambda a: scores[a], reverse=True)
    return sorted_apps[:5] if sorted_apps else []


def get_models_for_apps(apps: list[str]) -> list[dict]:
    """Returns model summaries for the given apps."""
    pmap = get_map()
    result = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        for m in app_data.get("models", []):
            fk_summary = [
                f"{f['name']} -> {f['related_model']}"
                for f in m.get("fields", [])
                if f.get("related_model")
            ]
            result.append({
                "app": app,
                "model": m["name"],
                "file": m["file"],
                "fk_relations": fk_summary,
            })
    return result


def get_viewsets_for_apps(apps: list[str]) -> list[dict]:
    """Returns viewset summaries for the given apps."""
    pmap = get_map()
    result = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        for vs in app_data.get("viewsets", []):
            result.append({
                "app": app,
                "viewset": vs["name"],
                "file": vs["file"],
                "bases": vs.get("bases", []),
                "actions": vs.get("actions", []),
            })
    return result


def get_endpoints_for_apps(apps: list[str]) -> list[dict]:
    """Returns endpoint summaries for the given apps."""
    pmap = get_map()
    endpoints = pmap.get("endpoints", [])
    result = [e for e in endpoints if e.get("app") in apps]
    return result


def get_frontend_consumers(apps: list[str]) -> list[dict]:
    """
    Returns Vue files that make API calls to endpoints belonging to the given apps.
    Matches by URL prefix.
    """
    pmap = get_map()
    cross = pmap.get("cross_refs", {})
    fe_to_ep = cross.get("frontend_to_endpoint", {})

    # Build app prefixes
    prefixes = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        prefix = app_data.get("api_prefix", f"api/v1/{app}")
        prefixes.append(prefix)

    result = []
    for fe_path, calls in fe_to_ep.items():
        matching_calls = [
            c for c in calls
            if any(pref in c.get("url", "") for pref in prefixes)
        ]
        if matching_calls:
            result.append({
                "file": fe_path,
                "api_calls": matching_calls,
            })
    return result


def get_stores_for_apps(apps: list[str]) -> list[dict]:
    """Returns Pinia stores that call endpoints in the given apps."""
    pmap = get_map()
    cross = pmap.get("cross_refs", {})
    store_to_ep = cross.get("store_to_endpoint", {})
    prefixes = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        prefix = app_data.get("api_prefix", f"api/v1/{app}")
        prefixes.append(prefix)

    result = []
    for store_id, calls in store_to_ep.items():
        matching = [c for c in calls if any(p in c.get("url", "") for p in prefixes)]
        if matching:
            result.append({"store": store_id, "calls": matching})
    return result


def get_serializers_for_apps(apps: list[str]) -> list[dict]:
    pmap = get_map()
    result = []
    for app in apps:
        for s in pmap.get("apps", {}).get(app, {}).get("serializers", []):
            result.append({"app": app, "serializer": s["name"], "file": s["file"]})
    return result


def get_services_for_apps(apps: list[str]) -> list[dict]:
    pmap = get_map()
    result = []
    for app in apps:
        for s in pmap.get("apps", {}).get(app, {}).get("services", []):
            result.append({"app": app, **s})
    return result


# ---------------------------------------------------------------------------
# IMPACT REPORT (human-readable + LLM prompt injection)
# ---------------------------------------------------------------------------

def build_impact_context(task: str, extra_apps: list[str] | None = None) -> str:
    """
    Builds a compact impact analysis string to inject into LLM prompts.
    Automatically detects affected apps from the task text and returns
    a structured summary of what components are impacted.
    """
    pmap = get_map()
    if not pmap:
        return ""

    detected_apps = find_affected_apps(task)
    if extra_apps:
        for a in extra_apps:
            if a not in detected_apps:
                detected_apps.append(a)

    if not detected_apps:
        return ""

    lines = ["=== IMPACTO EN EL PROYECTO (AUTO-ANALISIS) ===",
             f"Apps afectadas: {', '.join(detected_apps)}", ""]

    # Models
    models = get_models_for_apps(detected_apps)
    if models:
        lines.append("MODELOS AFECTADOS:")
        for m in models[:12]:
            fk = f"  FK: {', '.join(m['fk_relations'][:3])}" if m.get("fk_relations") else ""
            lines.append(f"  [{m['app']}] {m['model']}{fk}")
        lines.append("")

    # Serializers
    serializers = get_serializers_for_apps(detected_apps)
    if serializers:
        lines.append("SERIALIZERS:")
        for s in serializers[:8]:
            lines.append(f"  [{s['app']}] {s['serializer']} — {s['file']}")
        lines.append("")

    # ViewSets
    viewsets = get_viewsets_for_apps(detected_apps)
    if viewsets:
        lines.append("VIEWSETS:")
        for vs in viewsets[:8]:
            actions_str = ", ".join(vs["actions"][:5])
            lines.append(f"  [{vs['app']}] {vs['viewset']} ({actions_str}) — {vs['file']}")
        lines.append("")

    # Endpoints
    endpoints = get_endpoints_for_apps(detected_apps)
    if endpoints:
        lines.append("ENDPOINTS REST:")
        for ep in endpoints[:10]:
            methods = "/".join(ep.get("http_methods", []))
            lines.append(f"  {methods} {ep['endpoint']} -> {ep['viewset']}")
        lines.append("")

    # Frontend consumers
    fe_consumers = get_frontend_consumers(detected_apps)
    if fe_consumers:
        lines.append("FRONTEND QUE CONSUME ESTOS ENDPOINTS:")
        for fe in fe_consumers[:8]:
            calls = ", ".join(f"{c['method']} {c['url'][:40]}" for c in fe["api_calls"][:2])
            lines.append(f"  {fe['file']} ({calls})")
        lines.append("")

    # Stores
    stores = get_stores_for_apps(detected_apps)
    if stores:
        lines.append("PINIA STORES AFECTADOS:")
        for s in stores[:5]:
            lines.append(f"  {s['store']}")
        lines.append("")

    lines.append("=== FIN ANALISIS DE IMPACTO ===")
    return "\n".join(lines)


def build_impact_report(task: str, extra_apps: list[str] | None = None) -> dict:
    """
    Returns a structured dict for programmatic use (e.g., API responses).
    """
    pmap = get_map()
    if not pmap:
        return {"apps": [], "models": [], "viewsets": [], "endpoints": [],
                "frontend_files": [], "stores": []}

    detected_apps = find_affected_apps(task)
    if extra_apps:
        for a in extra_apps:
            if a not in detected_apps:
                detected_apps.append(a)

    return {
        "apps": detected_apps,
        "models": get_models_for_apps(detected_apps),
        "serializers": get_serializers_for_apps(detected_apps),
        "viewsets": get_viewsets_for_apps(detected_apps),
        "endpoints": get_endpoints_for_apps(detected_apps),
        "frontend_files": get_frontend_consumers(detected_apps),
        "stores": get_stores_for_apps(detected_apps),
        "services": get_services_for_apps(detected_apps),
    }
