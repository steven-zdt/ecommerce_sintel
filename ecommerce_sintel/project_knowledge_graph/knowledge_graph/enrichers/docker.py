"""
Enricher: nodos DockerService desde docker-compose.yml (Fase 5, PLAN_MAESTRO_
DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08). Extraido de ai_engine/
docker_graph.py. Solo lectura de `ecommerce_sintel/docker-compose.yml` -- este
modulo nunca escribe ni ejecuta Docker.

Nodo `DockerService`: un nodo por cada clave bajo `services:`.
Arista `DEPENDS_ON`: DockerService -> DockerService, 1:1 desde el
`depends_on:` real de cada servicio -- no heuristica, traduccion directa del
YAML.
Arista `DEPLOYS_TO`: App -> el `DockerService` que mas probablemente lo
hospeda, por convencion de nombre.
"""
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]


def _resolve_compose_path() -> Path:
    """Mismo criterio que config.py::_resolve_base_dir() -- docker-compose.yml
    vive dentro de ecommerce_sintel/, mismo problema de mountpoint dentro del
    contenedor sintel_ai."""
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path) / "docker-compose.yml"
    return REPO_ROOT / "ecommerce_sintel" / "docker-compose.yml"


COMPOSE_PATH = _resolve_compose_path()

# Mapeo explicito servicio Docker -> App/Service real que hospeda (no todos
# los servicios tienen una App Django 1:1 -- ollama/chromadb/nginx no).
SERVICE_TO_APP = {
    "django": None,       # hospeda TODAS las apps Django, no una sola -- no se linkea 1:1
    "sintel_ai": "ai_engine",
}


def load_compose() -> dict:
    if not COMPOSE_PATH.exists():
        return {}
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8")) or {}


# ---- Configuration/Infrastructure Graph (Fase 9, Site Knowledge Graph, ----
# 2026-08-10) --------------------------------------------------------------
#
# `DockerService -PROVIDES-> EnvVar`: los servicios reales de este proyecto
# (django/sintel_ai/celery_*) NO declaran variables individuales en
# `environment:` -- usan `env_file: .env` (compartido), verificado real en
# docker-compose.yml. Leer NOMBRES de variable (nunca valores) desde
# `.env.production.example` -- la PLANTILLA versionada explicitamente sin
# secretos ("PLANTILLA .env.production -- sin secretos, si versionable"),
# NUNCA desde `.env`/`.env.production` reales (contienen secretos reales).
# Regla 18 del plan ("no guardar secretos, no almacenar tokens") aplicada
# desde el origen: no se lee el archivo con secretos, ni siquiera para
# extraer solo nombres.

def _resolve_env_template_path() -> Path:
    """[CORREGIDO -- bug real de ruta encontrado y corregido, no una
    reescritura preventiva] `.env.production.example` vive DENTRO de
    `ecommerce_sintel/` (`ecommerce_sintel/.env.production.example`), NO
    en la raiz del repo -- verificado real con `find`. La primera version
    buscaba en `REPO_ROOT` directo, nunca encontraba el archivo, y
    `PROVIDES` quedaba en 0 aristas en todo el grafo en silencio. Mismo
    criterio que `_resolve_compose_path()` (CODEBASE_PATH primero, para
    consistencia dentro del contenedor sintel_ai)."""
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path) / ".env.production.example"
    return REPO_ROOT / "ecommerce_sintel" / ".env.production.example"


_ENV_TEMPLATE_PATH = _resolve_env_template_path()
_ENV_VAR_NAME_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.MULTILINE)


def _load_env_template_var_names() -> list[str]:
    if not _ENV_TEMPLATE_PATH.exists():
        return []
    text = _ENV_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
    return sorted(set(_ENV_VAR_NAME_RE.findall(text)))


_PORT_MAPPING_RE = re.compile(r"^(\d+)(?:/(tcp|udp))?:")


def _extract_host_ports(port_specs: list) -> list[dict]:
    """`ports:` de docker-compose puede ser `"8000:8000"` (string) o
    `{published: 8000, target: 8000}` (dict, sintaxis larga) -- solo el
    puerto HOST (published) importa para "que esta expuesto al exterior",
    el puerto del container es un detalle interno."""
    ports = []
    for spec in port_specs or []:
        if isinstance(spec, str):
            m = _PORT_MAPPING_RE.match(spec)
            if m:
                ports.append({"port": m.group(1), "protocol": m.group(2) or "tcp"})
        elif isinstance(spec, dict) and spec.get("published"):
            ports.append({"port": str(spec["published"]), "protocol": spec.get("protocol", "tcp")})
    return ports


def enrich_with_docker(kg) -> dict:
    from project_knowledge_graph.knowledge_graph.relations import Node

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

    # EXPOSES: DockerService -> Port (Fase 9, 2026-08-10).
    port_edges = 0
    for svc_name, svc_def in services.items():
        nid = f"docker:{svc_name}"
        for p in _extract_host_ports((svc_def or {}).get("ports")):
            port_nid = f"port:{p['port']}/{p['protocol']}"
            kg.add_node(Node(port_nid, "Port", p["port"], meta={"protocol": p["protocol"]}))
            kg.add_edge(nid, port_nid, "EXPOSES")
            port_edges += 1

    # PROVIDES: DockerService -> EnvVar (Fase 9, 2026-08-10) -- solo para
    # servicios con `env_file:` real (patron dominante de este proyecto),
    # matcheando contra los EnvVar reales ya construidos en Fase 2 (los que
    # el codigo Python realmente lee via config()/env()) -- no CUALQUIER
    # nombre del template cuenta, solo los que el grafo ya sabe que se usan.
    provides_edges = 0
    template_var_names = _load_env_template_var_names()
    if template_var_names:
        existing_env_var_ids = {n.name: n.id for n in kg.nodes_of_type("EnvVar")}
        for svc_name, svc_def in services.items():
            if not (svc_def or {}).get("env_file"):
                continue
            nid = f"docker:{svc_name}"
            for var_name in template_var_names:
                env_nid = existing_env_var_ids.get(var_name)
                if env_nid:
                    kg.add_edge(nid, env_nid, "PROVIDES")
                    provides_edges += 1

    return {"docker_service_nodes": added, "depends_on_edges": depends_edges,
            "exposes_port_edges": port_edges, "provides_envvar_edges": provides_edges,
            "deploys_to_edges": linked}
