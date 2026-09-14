"""
ProjectMapBuilder -- ensambla PROJECT_MAP.json a partir del scanner (Fase 4,
PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08). Extraido de
ai_engine/auditor.py::ProjectAuditor (la parte de construccion del mapa --
NO incluye la cadena hacia knowledge_graph/dependency_graph/memory/manifests
que el auditor original hacia en su run(); eso ahora vive en audit/auditor.py
como pipeline explicito, ver Fase 8).

SOURCE CODE -> SCANNER -> PROJECT_MAP. Responde "que existe en el proyecto",
no "como esta relacionado" (eso es knowledge_graph/).
"""
import datetime
import json
from typing import Any

from project_knowledge_graph.config import DJANGO_APPS, FRONTEND_DIR, PROJECT_MAP_PATH, BASE_DIR
from project_knowledge_graph.scanner.project_scanner import scan_app, scan_frontend


class ProjectMapBuilder:
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
                "views": [], "components": [], "composables": [],
                "stores": [], "router": [], "layouts": [], "modules": [],
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

    def build_cross_refs(self):
        cross = self.project_map["cross_refs"]

        for app_name, app_data in self.project_map["apps"].items():
            prefix = app_data.get("api_prefix", f"api/v1/{app_name}")
            for pat in app_data.get("url_patterns", []):
                if pat["type"] == "router":
                    endpoint = f"{prefix}/{pat['prefix']}"
                    vs = pat.get("viewset", "")
                    cross["endpoint_to_viewset"][endpoint] = {
                        "viewset": vs, "app": app_name, "basename": pat.get("basename"),
                    }

        for app_name, app_data in self.project_map["apps"].items():
            for vs in app_data.get("viewsets", []):
                vs_name = vs["name"]
                for suffix in ("ViewSet", "APIView", "View"):
                    if vs_name.endswith(suffix):
                        model_name = vs_name[:-len(suffix)]
                        for m in app_data.get("models", []):
                            if m["name"] == model_name:
                                cross["model_to_viewset"].setdefault(
                                    f"{app_name}.{model_name}", []
                                ).append(f"{app_name}.{vs_name}")

        fe = self.project_map.get("frontend", {})
        for group in ("views", "components", "composables", "stores", "misc"):
            for entry in fe.get(group, []):
                calls = entry.get("api_calls", [])
                if calls:
                    cross["frontend_to_endpoint"][entry["path"]] = [
                        {"method": c["method"], "url": c["url"]} for c in calls
                    ]

        for store in fe.get("stores", []):
            calls = store.get("api_calls", [])
            if calls:
                store_id = store.get("store_info", {}).get("store_id", store["path"])
                cross["store_to_endpoint"][store_id] = calls

    def build_endpoints_list(self):
        endpoints = []
        cross = self.project_map["cross_refs"]
        for endpoint, info in cross["endpoint_to_viewset"].items():
            app_name = info["app"]
            app_data = self.project_map["apps"].get(app_name, {})
            vs_name = info["viewset"]
            vs_data = next((v for v in app_data.get("viewsets", []) if v["name"] == vs_name), {})
            endpoints.append({
                "endpoint": endpoint, "app": app_name, "viewset": vs_name,
                "actions": vs_data.get("actions", []), "basename": info.get("basename"),
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

    def build(self, verbose: bool = True) -> dict:
        """Escanea todas las apps Django + frontend, arma cross-refs y
        endpoints, escribe PROJECT_MAP.json. No toca KG/DG/memory/manifests --
        eso es responsabilidad de audit/auditor.py (Fase 8)."""
        self.project_map["meta"]["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if verbose:
            print("Auditando apps Django...")
        for app_name in DJANGO_APPS:
            if verbose:
                print(f"  [{app_name}]", end=" ", flush=True)
            app_data = scan_app(app_name, DJANGO_APPS)
            if app_data:
                self.project_map["apps"][app_name] = app_data
                self.project_map["meta"]["apps"].append(app_name)
                if verbose:
                    m = len(app_data.get("models", []))
                    vs = len(app_data.get("viewsets", []))
                    ep = len(app_data.get("url_patterns", []))
                    print(f"models={m} viewsets={vs} endpoints={ep}")
            elif verbose:
                print("(no encontrada)")

        if verbose:
            print("\nAuditando frontend...")
        fe_data = scan_frontend()
        self.project_map["frontend"] = fe_data
        if verbose:
            for k, v in fe_data.items():
                print(f"  {k}: {len(v)} archivos")

        if verbose:
            print("\nConstruyendo cross-references...")
        self.build_cross_refs()
        self.build_endpoints_list()

        PROJECT_MAP_PATH.write_text(
            json.dumps(self.project_map, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if verbose:
            print(f"\nPROJECT_MAP.json escrito en: {PROJECT_MAP_PATH}")
            print(f"Tamano: {PROJECT_MAP_PATH.stat().st_size / 1024:.1f} KB")

        return self.project_map


def build_project_map(verbose: bool = True) -> dict:
    return ProjectMapBuilder().build(verbose=verbose)
