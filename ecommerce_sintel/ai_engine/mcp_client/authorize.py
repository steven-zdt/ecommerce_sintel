"""
Autorizacion one-shot del MCP oficial de Meta Ads.

Se ejecuta UNA vez, a mano, dentro del contenedor sintel_ai:

    docker compose -f docker-compose.yml run --rm -p 8765:8765 \
        sintel_ai python -m mcp_client.authorize

Que hace:
  1. Arranca un servidor HTTP local en MCP_OAUTH_CALLBACK_PORT (8765) para
     capturar el redirect del OAuth.
  2. Imprime (y trata de abrir) la URL de autorizacion de Meta. Tu inicias
     sesion en el navegador con la cuenta de Facebook que administra el
     Business Manager y aceptas los permisos.
  3. El SDK intercambia el `code` por tokens y FileTokenStorage los guarda en
     MCP_TOKEN_STORE_DIR (volumen montado, no versionado).
  4. Lista las tools del servidor como verificacion.

A partir de aqui MetaAdsMCPClient refresca el token solo, sin interaccion.
Reautorizar solo si Meta revoca el acceso.
"""
import asyncio
import logging
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from config import MCP_OAUTH_CALLBACK_PORT, MCP_TOKEN_STORE_DIR
from mcp_client.client import MetaAdsMCPClient, MCPClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mcp_client.authorize")


class _CallbackCatcher:
    """Servidor HTTP efimero que captura ?code=&state= del redirect OAuth."""

    def __init__(self, port: int):
        self._port = port
        self._result: dict = {}
        self._done = threading.Event()

    def _handler_factory(self):
        catcher = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):  # silencio
                pass

            def do_GET(self):
                params = parse_qs(urlparse(self.path).query)
                catcher._result = {
                    "code": (params.get("code") or [None])[0],
                    "state": (params.get("state") or [None])[0],
                    "error": (params.get("error") or [None])[0],
                }
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                ok = catcher._result.get("code") and not catcher._result.get("error")
                msg = "Autorizacion recibida. Puedes cerrar esta pestana." if ok else \
                      f"Fallo la autorizacion: {catcher._result.get('error')}"
                self.wfile.write(f"<html><body><p>{msg}</p></body></html>".encode("utf-8"))
                catcher._done.set()

        return Handler

    async def wait_for_code(self) -> tuple[str, str | None]:
        server = HTTPServer(("0.0.0.0", self._port), self._handler_factory())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._done.wait)
        finally:
            server.shutdown()
        if self._result.get("error") or not self._result.get("code"):
            raise MCPClientError(f"OAuth fallo: {self._result.get('error') or 'sin code'}")
        return self._result["code"], self._result.get("state")


async def _run() -> int:
    client = MetaAdsMCPClient()
    catcher = _CallbackCatcher(MCP_OAUTH_CALLBACK_PORT)

    async def _redirect_handler(auth_url: str) -> None:
        print("\n" + "=" * 72)
        print("Abre esta URL en tu navegador e inicia sesion con la cuenta de")
        print("Facebook que administra el Business Manager de Meta Ads:\n")
        print(f"  {auth_url}\n")
        print("=" * 72 + "\n")
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

    async def _callback_handler() -> tuple[str, str | None]:
        return await catcher.wait_for_code()

    provider = client.build_oauth_provider(
        redirect_handler=_redirect_handler,
        callback_handler=_callback_handler,
    )

    print(f"[authorize] servidor de callback en http://localhost:{MCP_OAUTH_CALLBACK_PORT}/callback")
    print(f"[authorize] los tokens se guardaran en {MCP_TOKEN_STORE_DIR}/\n")

    try:
        async with client._open_session(auth_provider=provider) as session:
            result = await session.list_tools()
    except MCPClientError as exc:
        print(f"\n[authorize] ERROR: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"\n[authorize] ERROR inesperado: {type(exc).__name__}: {exc}")
        return 1

    tools = getattr(result, "tools", [])
    print(f"\n[authorize] OK. Conexion establecida. {len(tools)} tools disponibles.")
    print("[authorize] Ejemplos:", ", ".join(t.name for t in tools[:8]) or "(ninguna)")
    print("\n[authorize] Ahora pon MCP_META_ADS_ENABLED=true en el .env de sintel_ai")
    print("            y reinicia el contenedor.")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
