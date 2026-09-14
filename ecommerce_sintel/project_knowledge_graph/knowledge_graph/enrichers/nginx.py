"""
Enricher: nodos NginxRoute desde `nginx-common.conf` (Fase 9 "Configuration/
Infrastructure Graph", Site Knowledge Graph, 2026-08-10). Solo lectura --
nunca escribe ni recarga nginx.

Nodo `NginxRoute`: un nodo por bloque `location` real.
Arista `ROUTES_TO`: NginxRoute -> DockerService, resuelto contra
`proxy_pass` -- verificado real contra nginx-common.conf:
  - `location / { proxy_pass $django_upstream; }` con
    `set $django_upstream http://django:8000;` declarado antes -- la forma
    DOMINANTE real (indireccion via variable, no literal), documentada en
    el propio archivo como fix de un bug real de DNS caching de nginx.
  - `location /api/v1/internal/ { deny all; return 403; }` -- sin
    `proxy_pass`, NO genera arista ROUTES_TO (bloqueado a proposito, no
    enrutado a ningun DockerService).
"""
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _resolve_ecommerce_dir() -> Path:
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    return REPO_ROOT / "ecommerce_sintel"


NGINX_CONF_CANDIDATES = ("nginx-common.conf", "nginx.conf")

_SET_UPSTREAM_RE = re.compile(r"set\s+\$(\w+)\s+http://([\w.-]+)(?::\d+)?\s*;")
# [CORREGIDO -- bug real encontrado, no una reescritura preventiva]: sin
# anclar a inicio de linea ni excluir '\n' de la captura, "location" matcheaba
# como SUBSTRING dentro de "geolocation=()" (un header Permissions-Policy
# real de este archivo), y la captura no-greedy [^\{]+? igual se extendia
# cientos de lineas hasta el proximo '{' real -- un NginxRoute con el path
# de TODO ese texto intermedio. Ancla a inicio de linea + prohibe '\n' en la
# ruta capturada (una directiva `location` real siempre es una sola linea).
_LOCATION_RE = re.compile(r"(?:^|\n)[ \t]*location\s*(=)?\s*([^\{\n]+?)\s*\{", re.MULTILINE)
_PROXY_PASS_RE = re.compile(r"proxy_pass\s+(\$\w+|http://[\w.-]+(?::\d+)?)\s*;")


def _find_block_end(text: str, open_brace_idx: int) -> int | None:
    """Balance de llaves simple -- los bloques `location` de este proyecto
    no anidan strings/comentarios con llaves sin escapar, un balance
    directo (sin el manejo de strings que si hace frontend_scanner.py)
    es suficiente para config nginx real."""
    depth = 0
    for i in range(open_brace_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def extract_nginx_routes(text: str) -> list[dict]:
    """Cada bloque `location` real con su `proxy_pass` resuelto (via
    variable `set $x http://servicio:puerto;` o literal `http://servicio`)
    -- `target_service` es `None` cuando el bloque no proxea a nada
    (archivos estaticos, `deny all`, etc.), correctamente excluido de
    ROUTES_TO por el enricher."""
    upstream_by_var = {var: svc for var, svc in _SET_UPSTREAM_RE.findall(text)}

    routes = []
    for m in _LOCATION_RE.finditer(text):
        exact, path = m.group(1), m.group(2).strip()
        brace_idx = m.end() - 1
        end_idx = _find_block_end(text, brace_idx)
        if end_idx is None:
            continue
        block = text[brace_idx:end_idx]

        target_service = None
        pp = _PROXY_PASS_RE.search(block)
        if pp:
            value = pp.group(1)
            if value.startswith("$"):
                target_service = upstream_by_var.get(value[1:])
            else:
                target_service = value.replace("http://", "").split(":")[0]

        routes.append({"path": path, "exact": bool(exact), "target_service": target_service})
    return routes


def load_nginx_config_text() -> str:
    ecommerce_dir = _resolve_ecommerce_dir()
    for name in NGINX_CONF_CANDIDATES:
        path = ecommerce_dir / name
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def enrich_with_nginx(kg) -> dict:
    from project_knowledge_graph.knowledge_graph.relations import Node

    text = load_nginx_config_text()
    if not text:
        return {"nginx_route_nodes": 0, "routes_to_edges": 0}

    routes = extract_nginx_routes(text)
    added = 0
    routes_to_edges = 0
    for route in routes:
        nid = f"nginx:{route['path']}"
        kg.add_node(Node(nid, "NginxRoute", route["path"],
                         meta={"exact": route["exact"], "target_service": route["target_service"]}))
        added += 1
        if route["target_service"]:
            docker_nid = f"docker:{route['target_service']}"
            if docker_nid in kg.nodes:
                kg.add_edge(nid, docker_nid, "ROUTES_TO")
                routes_to_edges += 1

    return {"nginx_route_nodes": added, "routes_to_edges": routes_to_edges}
