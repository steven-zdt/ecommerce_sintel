"""Arranque: python -m mcp_server. Streamable HTTP en MCP_HOST:MCP_PORT, ruta /mcp. Falla cerrado si la configuracion no es segura."""
import sys

from . import audit, config
from .server import App, build_server, transport_security


def main() -> None:
    settings = config.load()
    audit.setup_logging(settings.log_level)
    settings.validate()
    if not settings.enabled:
        audit.app_logger.warning("MCP_ENABLED=false: el servidor MCP esta deshabilitado y no arranca.")
        sys.exit(0)
    server = build_server(App(settings))
    audit.app_logger.info("Iniciando SINTEL MCP en %s:%s (auth=%s, perfil por defecto=%s)", settings.host, settings.port, settings.auth_mode, settings.default_profile)
    server.run("streamable-http", host=settings.host, port=settings.port, transport_security=transport_security(settings), max_request_body_size=settings.max_body_bytes)


if __name__ == "__main__":
    main()
