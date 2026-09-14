"""
ai_manifest.py - AI Manifest Generator (Phases 12 & 14)

Generates AI_MANIFEST.json per app — a machine-readable contract
that captures everything an AI agent needs to know before touching an app:
  - Architecture overview
  - Entry points (ViewSets, URLs)
  - Data contracts (Models, Serializers)
  - Service contracts (Commands, Selectors)
  - Events produced/consumed
  - Frontend consumers
  - Test coverage
  - Known constraints and HOT_FIX notes
  - Business rules specific to this app
  - Dependencies on other apps
  - What depends on this app

Also generates a MASTER_MANIFEST.json that links all app manifests.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

AI_ENGINE_DIR   = Path(__file__).resolve().parent
MAP_PATH        = AI_ENGINE_DIR / "PROJECT_MAP.json"
DG_PATH         = AI_ENGINE_DIR / "DEPENDENCY_GRAPH.json"
KG_PATH         = AI_ENGINE_DIR / "KNOWLEDGE_GRAPH.json"
GM_PATH         = AI_ENGINE_DIR / "GLOBAL_MEMORY.json"
APP_MEMORY_DIR  = AI_ENGINE_DIR / "APP_MEMORY"
MANIFESTS_DIR   = AI_ENGINE_DIR / "AI_MANIFESTS"
MASTER_MANIFEST = AI_ENGINE_DIR / "MASTER_MANIFEST.json"

BASE_DIR = AI_ENGINE_DIR.parent / "ecommerce_sintel"


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def build_app_manifest(app_name: str) -> dict:
    """
    Builds a complete AI_MANIFEST for one app.
    Aggregates data from PROJECT_MAP, DEPENDENCY_GRAPH, KNOWLEDGE_GRAPH, APP_MEMORY.
    """
    pmap   = _load_json(MAP_PATH)
    dg     = _load_json(DG_PATH)
    gm     = _load_json(GM_PATH)
    am     = _load_json(APP_MEMORY_DIR / f"{app_name}.json")
    kg     = _load_json(KG_PATH)

    app_data = pmap.get("apps", {}).get(app_name, {})
    if not app_data:
        return {"app": app_name, "error": "App not found in PROJECT_MAP"}

    # Build node index from KG for this app
    app_nodes = [n for n in kg.get("nodes", []) if n.get("app") == app_name]
    node_by_type: dict[str, list] = {}
    for n in app_nodes:
        node_by_type.setdefault(n["type"], []).append(n)

    # Endpoints
    endpoints = [ep for ep in pmap.get("endpoints", []) if ep.get("app") == app_name]

    # Frontend consumers (from dependency graph)
    fe_consumers: dict[str, list] = {}
    for ep in endpoints:
        ep_str = ep.get("endpoint", "")
        consumers = dg.get("endpoint_consumers", {}).get(ep_str, [])
        if consumers:
            fe_consumers[ep_str] = consumers

    # What this app depends on (FK relations to other apps)
    dependencies: set[str] = set()
    for m in app_data.get("models", []):
        for f in m.get("fields", []):
            rel = f.get("related_model", "")
            if rel and rel not in ("self", "settings.AUTH_USER_MODEL"):
                # Try to find which app owns this model
                for other_app, other_data in pmap.get("apps", {}).items():
                    if other_app == app_name:
                        continue
                    model_names = [m2["name"] for m2 in other_data.get("models", [])]
                    target = rel.split(".")[-1]
                    if target in model_names:
                        dependencies.add(other_app)
                        break

    # What depends on this app (reverse lookup)
    dependents: set[str] = set()
    for other_app, other_data in pmap.get("apps", {}).items():
        if other_app == app_name:
            continue
        for m in other_data.get("models", []):
            for f in m.get("fields", []):
                rel = f.get("related_model", "")
                if rel:
                    target = rel.split(".")[-1]
                    our_models = [m2["name"] for m2 in app_data.get("models", [])]
                    if target in our_models:
                        dependents.add(other_app)
                        break

    # Blast radius summary (how many things break if we change models in this app)
    blast_entries = {}
    for m in app_data.get("models", []):
        key = f"{app_name}.{m['name']}"
        impact = dg.get("change_impact", {}).get(key, {})
        if impact:
            total = sum(len(v) for v in impact.values())
            blast_entries[m["name"]] = {"types_affected": list(impact.keys()), "total": total}

    # Business rules relevant to this app
    relevant_rules = []
    app_lower = app_name.lower()
    for rule in gm.get("critical_rules", []):
        rule_text = rule.get("rule", "").lower() + rule.get("why", "").lower()
        if app_lower in rule_text or any(
            kw in rule_text for kw in _app_rule_keywords.get(app_name, [])
        ):
            relevant_rules.append(rule)

    # File map (non-migration files)
    file_map: dict[str, list] = {}
    for f in app_data.get("files", []):
        role = f.get("role", "misc")
        if role != "migration":
            file_map.setdefault(role, []).append(f["path"])

    import datetime
    return {
        "app": app_name,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "api_prefix": app_data.get("api_prefix", f"api/v1/{app_name}"),
        "purpose": am.get("purpose", ""),
        "architecture": {
            "models": [
                {
                    "name": m["name"],
                    "file": m.get("file", ""),
                    "fk_relations": [f for f in m.get("fields", []) if f.get("related_model")],
                }
                for m in app_data.get("models", [])
            ],
            "serializers": [
                {"name": s["name"], "file": s.get("file", "")}
                for s in app_data.get("serializers", [])
            ],
            "viewsets": [
                {
                    "name": vs["name"],
                    "file": vs.get("file", ""),
                    "bases": vs.get("bases", []),
                    "actions": vs.get("actions", []),
                }
                for vs in app_data.get("viewsets", [])
            ],
            "services": app_data.get("services", []),
            "selectors": app_data.get("selectors", []),
            "management_commands": app_data.get("management_commands", []),
            "consumers": app_data.get("consumers", []),
            "tasks": app_data.get("tasks", []),
            "permissions": app_data.get("permissions", []),
            "file_map": file_map,
            "migrations": len(app_data.get("migrations", [])),
        },
        "endpoints": endpoints,
        "frontend_consumers": fe_consumers,
        "dependencies": {
            "depends_on": sorted(dependencies),
            "depended_by": sorted(dependents),
        },
        "blast_radius": blast_entries,
        "service_contracts": {
            "commands": [s["name"] for s in app_data.get("services", [])
                         if "command" in s.get("role", "").lower()],
            "selectors": [s["name"] for s in app_data.get("services", [])
                          if "selector" in s.get("role", "").lower()],
        },
        "events": {
            "produces": am.get("events", []),
            "consumes": [],
        },
        "constraints": am.get("constraints", []),
        "known_issues": am.get("known_issues", []),
        "business_rules": relevant_rules,
        "url_patterns": app_data.get("url_patterns", []),
        "patterns": am.get("patterns", {}),
        "TODO": am.get("TODO", []),
        "BUG": am.get("BUG", []),
        "HOT_FIX": am.get("HOT_FIX", []),
        "decisions": am.get("decisions", []),
    }


# App-specific rule keywords for matching business rules
_app_rule_keywords: dict[str, list[str]] = {
    "shop":               ["product", "vendor", "decimal"],
    "orders":             ["order", "coupon", "discount", "checkout"],
    "cart":               ["cart", "cartitem"],
    "payment":            ["payment", "wompi", "webhook", "confirm_order_payment"],
    "inventory":          ["inventory", "stock", "select_for_update"],
    "notifications":      ["notification", "dispatch_notification", "on_commit"],
    "accounts":           ["profile", "user_type", "role"],
    "users":              ["admin", "isadminuser", "is_staff"],
    "renting":            ["rental", "alquiler"],
    "technical_services": ["service", "servicebooking"],
    "support":            ["chat", "consumer"],
    "core":               ["home", "feed"],
    "quotes":             ["quote", "quotation"],
    "marketing":          ["marketing", "campaign"],
    "dashboard":          ["dashboard", "bff"],
}


def build_all_manifests() -> dict[str, dict]:
    """Build AI_MANIFEST.json for every app."""
    MANIFESTS_DIR.mkdir(exist_ok=True)
    pmap = _load_json(MAP_PATH)
    manifests: dict[str, dict] = {}
    app_names = list(pmap.get("apps", {}).keys())

    for app_name in app_names:
        manifest = build_app_manifest(app_name)
        manifests[app_name] = manifest
        out_path = MANIFESTS_DIR / f"{app_name}_MANIFEST.json"
        out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[ai_manifest] Written %s_MANIFEST.json", app_name)

    # Master manifest index
    import datetime
    master = {
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "apps": app_names,
        "manifests": {
            app: str(MANIFESTS_DIR / f"{app}_MANIFEST.json")
            for app in app_names
        },
        "stats": {
            "total_apps": len(app_names),
            "total_endpoints": sum(len(m.get("endpoints", [])) for m in manifests.values()),
            "total_models": sum(len(m.get("architecture", {}).get("models", [])) for m in manifests.values()),
        },
        "global_rules_count": len(_load_json(GM_PATH).get("critical_rules", [])),
    }
    MASTER_MANIFEST.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[ai_manifest] Written MASTER_MANIFEST.json")
    return manifests


def get_manifest(app_name: str) -> dict:
    path = MANIFESTS_DIR / f"{app_name}_MANIFEST.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return build_app_manifest(app_name)


def get_manifests_for_apps(app_names: list[str]) -> list[dict]:
    return [get_manifest(a) for a in app_names]


def manifest_summary(app_name: str) -> str:
    """Compact text summary of a manifest for LLM prompt injection."""
    m = get_manifest(app_name)
    if not m or m.get("error"):
        return ""
    arch = m.get("architecture", {})
    lines = [
        f"=== AI_MANIFEST [{app_name}] ===",
        f"Purpose: {m.get('purpose', '')}",
        f"API prefix: {m.get('api_prefix', '')}",
        f"Models: {', '.join(a['name'] for a in arch.get('models', [])[:6])}",
        f"ViewSets: {', '.join(v['name'] for v in arch.get('viewsets', [])[:5])}",
        f"Depends on: {', '.join(m.get('dependencies', {}).get('depends_on', []))}",
        f"Depended by: {', '.join(m.get('dependencies', {}).get('depended_by', [])[:5])}",
    ]
    if m.get("constraints"):
        lines.append(f"Constraints: {m['constraints'][0][:80]}")
    if m.get("known_issues"):
        lines.append(f"Known issues: {m['known_issues'][0][:80]}")
    lines.append("=== FIN MANIFEST ===")
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    manifests = build_all_manifests()
    print(f"Generated {len(manifests)} app manifests in {MANIFESTS_DIR}")
    print(f"Master manifest: {MASTER_MANIFEST}")
