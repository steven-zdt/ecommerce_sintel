"""
Unit tests puros (sin I/O, texto sintetico) para knowledge_graph/enrichers/
nginx.py y las funciones nuevas de docker.py -- Fase 9 "Configuration/
Infrastructure Graph", Site Knowledge Graph, 2026-08-10. Modelado sobre
nginx-common.conf y docker-compose.yml reales.
"""
from project_knowledge_graph.knowledge_graph.enrichers.docker import (
    _extract_host_ports,
)
from project_knowledge_graph.knowledge_graph.enrichers.nginx import (
    extract_nginx_routes,
)


def test_extract_nginx_routes_resolves_proxy_pass_via_set_variable():
    """Patron real dominante de nginx-common.conf: `set $x http://svc:port;`
    + `proxy_pass $x;` -- documentado en el propio archivo como fix de un
    bug real de DNS caching de nginx."""
    text = (
        "resolver 127.0.0.11 valid=10s;\n"
        "set $django_upstream http://django:8000;\n"
        "\n"
        "location / {\n"
        "    proxy_pass $django_upstream;\n"
        "}\n"
    )
    routes = extract_nginx_routes(text)
    assert routes == [{"path": "/", "exact": False, "target_service": "django"}]


def test_extract_nginx_routes_resolves_literal_proxy_pass():
    text = "location / {\n    proxy_pass http://django;\n}\n"
    routes = extract_nginx_routes(text)
    assert routes[0]["target_service"] == "django"


def test_extract_nginx_routes_blocked_location_has_no_target():
    """`deny all; return 403;` -- bloqueado a proposito, sin proxy_pass, no
    debe generar un target_service inventado."""
    text = "location /api/v1/internal/ {\n    deny all;\n    return 403;\n}\n"
    routes = extract_nginx_routes(text)
    assert routes == [{"path": "/api/v1/internal/", "exact": False, "target_service": None}]


def test_extract_nginx_routes_does_not_match_geolocation_substring():
    """Bug real encontrado y corregido: 'location' matcheaba como substring
    dentro de 'geolocation=()' (un header Permissions-Policy real), con la
    captura no-greedy extendiendose cientos de lineas hasta el proximo '{'
    real -- verificado con un caso sintetico equivalente."""
    text = (
        'add_header Permissions-Policy "geolocation=(), camera=()" always;\n'
        "\n"
        "location / {\n"
        "    proxy_pass http://django;\n"
        "}\n"
    )
    routes = extract_nginx_routes(text)
    assert routes == [{"path": "/", "exact": False, "target_service": "django"}]


def test_extract_nginx_routes_exact_match_flag():
    text = "location = /favicon.ico {\n    alias /code/staticfiles/favicon.svg;\n}\n"
    routes = extract_nginx_routes(text)
    assert routes[0]["exact"] is True
    assert routes[0]["target_service"] is None


def test_extract_host_ports_handles_string_and_dict_forms():
    assert _extract_host_ports(["8000:8000"]) == [{"port": "8000", "protocol": "tcp"}]
    assert _extract_host_ports([{"published": 5432, "target": 5432}]) == [
        {"port": "5432", "protocol": "tcp"}
    ]


def test_extract_host_ports_ignores_container_only_port():
    """Un puerto SOLO de container (sin mapeo a host, ej. `"8000"` sin ':')
    no expone nada al exterior -- no deberia generar un nodo Port."""
    assert _extract_host_ports(["8000"]) == []
