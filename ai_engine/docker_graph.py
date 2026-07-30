"""
docker_graph.py - Fase 5 de AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md

Agrega nodos `DockerService` al Knowledge Graph, parseados SOLO LECTURA de
`ecommerce_sintel/docker-compose.yml` -- este modulo nunca escribe ni ejecuta
Docker, solo lee el YAML ya versionado. No requiere infraestructura nueva.

Nodo `DockerService`: un nodo por cada clave bajo `services:`.
Arista `DEPENDS_ON` (reutiliza el label ya existente, misma semantica que la
version Model->Model): DockerService -> DockerService, 1:1 desde el
`depends_on:` real de cada servicio -- no heuristica, es una traduccion
directa del YAML.
Arista `DEPLOYS_TO` (nueva, propuesta en §6.2 de la auditoria): App -> el
`DockerService` que mas probablemente lo hospeda, por convencion de nombre
ya usada en el propio compose (container_name: ecommerce_sintel_<algo>).
"""
import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_compose_path() -> Path:
    """Ver auditor.py::_resolve_base_dir() -- mismo fix (docker-compose.yml vive dentro
    de ecommerce_sintel/, mismo problema de mountpoint dentro del contenedor sintel_ai)."""
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path) / "docker-compose.yml"
    return REPO_ROOT / "ecommerce_sintel" / "docker-compose.yml"


COMPOSE_PATH = _resolve_compose_path()

# Mapeo explicito servicio Docker -> App/Service real que hospeda (no todos
# los 10 servicios tienen una App Django 1:1 -- ollama/chromadb/nginx no).
SERVICE_TO_APP = {
    "django": None,       # hospeda TODAS las apps Django, no una sola -- no se linkea 1:1
    "sintel_ai": "ai_engine",
}


def load_compose() -> dict:
    if not COMPOSE_PATH.exists():
        return {}
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8")) or {}


def enrich_with_docker(kg) -> dict:
    from knowledge_graph import Node

    compose = load_compose()
    services = compose.get("services", {})
    added = 0
    depends_edges = 0

    for svc_name, svc_def in services.items():
        nid = f"docker:{svc_name}"
        svc_def = svc_def or {}
        healthcheck = svc_def.get("healthcheck")
        kg.add_node(Node(
            nid, "DockerService", svc_name,
            meta={
                "image": svc_def.get("image"),
                "container_name": svc_def.get("container_name"),
                "has_healthcheck": healthcheck is not None,
                "ports": svc_def.get("ports", []),
                "restart": svc_def.get("restart"),
            },
        ))
        added += 1

    for svc_name, svc_def in services.items():
        nid = f"docker:{svc_name}"
        deps = (svc_def or {}).get("depends_on")
        if not deps:
            continue
        dep_names = deps.keys() if isinstance(deps, dict) else deps
        for dep_name in dep_names:
            dep_nid = f"docker:{dep_name}"
            if dep_nid in kg.nodes:
                kg.add_edge(nid, dep_nid, "DEPENDS_ON")
                depends_edges += 1

    linked = 0
    for svc_name in services:
        candidate_app = SERVICE_TO_APP.get(svc_name)
        app_nid = f"app:{candidate_app}" if candidate_app else None
        if app_nid and app_nid in kg.nodes:
            kg.add_edge(app_nid, f"docker:{svc_name}", "DEPLOYS_TO")
            linked += 1

    return {"docker_service_nodes": added, "depends_on_edges": depends_edges,
            "deploys_to_edges": linked}


if __name__ == "__main__":
    compose = load_compose()
    print(f"Servicios encontrados en docker-compose.yml: {list(compose.get('services', {}).keys())}")
