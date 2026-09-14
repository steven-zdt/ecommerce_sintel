"""
Interfaz de consulta sobre PROJECT_MAP -- entiende dependencias cross-app,
componentes impactados, y cadenas de endpoints. Extraido de ai_engine/
project_map.py (Fase 4, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH,
2026-08-08).
"""
from project_knowledge_graph.project_map.loader import get_map

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
    """Combina keywords de dominio + datos estructurales AST del PROJECT_MAP.
    Devuelve apps ordenadas por score de relevancia."""
    pmap = get_map()
    apps_data = pmap.get("apps", {})
    task_lower = task.lower()
    scores: dict[str, int] = {}

    for app_name, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in task_lower:
                scores[app_name] = scores.get(app_name, 0) + 2

    for app_name, app_data in apps_data.items():
        for m in app_data.get("models", []):
            name = m["name"].lower()
            if len(name) > 3 and name in task_lower:
                scores[app_name] = scores.get(app_name, 0) + 3
        for vs in app_data.get("viewsets", []):
            name = vs["name"].lower()
            for suffix in ("viewset", "apiview", "view"):
                name = name.replace(suffix, "")
            if len(name) > 3 and name in task_lower:
                scores[app_name] = scores.get(app_name, 0) + 2
        if app_name.replace("_", " ") in task_lower or app_name in task_lower:
            scores[app_name] = scores.get(app_name, 0) + 2
        prefix = app_data.get("api_prefix", "").lower().split("/")[-1]
        if len(prefix) > 3 and prefix in task_lower:
            scores[app_name] = scores.get(app_name, 0) + 1

    sorted_apps = sorted(scores, key=lambda a: scores[a], reverse=True)
    return sorted_apps[:5] if sorted_apps else []


def get_models_for_apps(apps: list[str]) -> list[dict]:
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
            result.append({"app": app, "model": m["name"], "file": m["file"], "fk_relations": fk_summary})
    return result


def get_viewsets_for_apps(apps: list[str]) -> list[dict]:
    pmap = get_map()
    result = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        for vs in app_data.get("viewsets", []):
            result.append({
                "app": app, "viewset": vs["name"], "file": vs["file"],
                "bases": vs.get("bases", []), "actions": vs.get("actions", []),
            })
    return result


def get_endpoints_for_apps(apps: list[str]) -> list[dict]:
    pmap = get_map()
    endpoints = pmap.get("endpoints", [])
    return [e for e in endpoints if e.get("app") in apps]


def get_frontend_consumers(apps: list[str]) -> list[dict]:
    """Vue files que llaman endpoints de las apps dadas (match por prefijo de URL)."""
    pmap = get_map()
    cross = pmap.get("cross_refs", {})
    fe_to_ep = cross.get("frontend_to_endpoint", {})

    prefixes = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        prefixes.append(app_data.get("api_prefix", f"api/v1/{app}"))

    result = []
    for fe_path, calls in fe_to_ep.items():
        matching_calls = [c for c in calls if any(pref in c.get("url", "") for pref in prefixes)]
        if matching_calls:
            result.append({"file": fe_path, "api_calls": matching_calls})
    return result


def get_stores_for_apps(apps: list[str]) -> list[dict]:
    pmap = get_map()
    cross = pmap.get("cross_refs", {})
    store_to_ep = cross.get("store_to_endpoint", {})
    prefixes = []
    for app in apps:
        app_data = pmap.get("apps", {}).get(app, {})
        prefixes.append(app_data.get("api_prefix", f"api/v1/{app}"))

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
# IMPACT REPORT (texto legible + inyeccion en prompt LLM)
# ---------------------------------------------------------------------------

def build_impact_context(task: str, extra_apps: list[str] | None = None) -> str:
    """Texto compacto de analisis de impacto para inyectar en prompts LLM."""
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

    models = get_models_for_apps(detected_apps)
    if models:
        lines.append("MODELOS AFECTADOS:")
        for m in models[:12]:
            fk = f"  FK: {', '.join(m['fk_relations'][:3])}" if m.get("fk_relations") else ""
            lines.append(f"  [{m['app']}] {m['model']}{fk}")
        lines.append("")

    serializers = get_serializers_for_apps(detected_apps)
    if serializers:
        lines.append("SERIALIZERS:")
        for s in serializers[:8]:
            lines.append(f"  [{s['app']}] {s['serializer']} - {s['file']}")
        lines.append("")

    viewsets = get_viewsets_for_apps(detected_apps)
    if viewsets:
        lines.append("VIEWSETS:")
        for vs in viewsets[:8]:
            actions_str = ", ".join(vs["actions"][:5])
            lines.append(f"  [{vs['app']}] {vs['viewset']} ({actions_str}) - {vs['file']}")
        lines.append("")

    endpoints = get_endpoints_for_apps(detected_apps)
    if endpoints:
        lines.append("ENDPOINTS REST:")
        for ep in endpoints[:10]:
            methods = "/".join(ep.get("http_methods", []))
            lines.append(f"  {methods} {ep['endpoint']} -> {ep['viewset']}")
        lines.append("")

    fe_consumers = get_frontend_consumers(detected_apps)
    if fe_consumers:
        lines.append("FRONTEND QUE CONSUME ESTOS ENDPOINTS:")
        for fe in fe_consumers[:8]:
            calls = ", ".join(f"{c['method']} {c['url'][:40]}" for c in fe["api_calls"][:2])
            lines.append(f"  {fe['file']} ({calls})")
        lines.append("")

    stores = get_stores_for_apps(detected_apps)
    if stores:
        lines.append("PINIA STORES AFECTADOS:")
        for s in stores[:5]:
            lines.append(f"  {s['store']}")
        lines.append("")

    lines.append("=== FIN ANALISIS DE IMPACTO ===")
    return "\n".join(lines)


def build_impact_report(task: str, extra_apps: list[str] | None = None) -> dict:
    """Version estructurada (dict) para uso programatico, ej. respuestas HTTP."""
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
