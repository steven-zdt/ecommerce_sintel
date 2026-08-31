"""
MetaGraphClient -- cliente HTTP aislado hacia la Graph API de Meta.

Equivalente arquitectonico de payment/online/wompi_client.py::WompiApiClient:
solo transporte + serializacion + normalizacion de errores. CERO logica de
negocio de Sintel aqui (nada de MarketingCampaign / ChatRoom / catalogo). Los
subclientes de dominio (whatsapp.py, y en fases posteriores marketing.py /
instagram.py / conversions.py) se construyen ENCIMA de esta clase.

Contrato de la Graph API usado (no asumido):
  - Auth: header "Authorization: Bearer <access_token>" (token de sistema de
    Meta Business). Igual que notifications/clients/whatsapp.py hoy.
  - Errores: envelope estandar {"error": {"message", "type", "code",
    "error_subcode", "fbtrace_id"}} con HTTP 4xx/5xx.
  - Paginacion por cursores: {"data": [...], "paging": {"cursors": {"after": ...},
    "next": "<url>"}}.
"""
import logging

import requests

from marketing.integrations.meta.exceptions import (
    MetaApiError,
    MetaApiTransientError,
    MetaAuthError,
    MetaConfigError,
    MetaRateLimitError,
)

logger = logging.getLogger(__name__)

_GRAPH_HOST = "https://graph.facebook.com"

# Error codes de Meta que significan "throttling", no un fallo del request.
# https://developers.facebook.com/docs/graph-api/overview/rate-limiting
_RATE_LIMIT_CODES = {4, 17, 32, 613, 80004, 80014}

# Error codes de Meta que significan "token / permisos", reintentar no ayuda.
_AUTH_CODES = {102, 190, 200, 210, 294, 458, 459, 463, 464, 467}

_DEFAULT_TIMEOUT_SECONDS = 15
_DEFAULT_PAGINATE_MAX_PAGES = 10


class MetaGraphClient:

    def __init__(self, *, integration_settings: dict | None = None):
        # Fachada de solo lectura sobre settings/.env -- mismo punto que usan
        # marketing/channels/*. El parametro es solo para tests.
        if integration_settings is None:
            from organization.services.selectors import OrganizationSelector
            integration_settings = OrganizationSelector.get_integration_settings()
        self._settings = integration_settings
        self._token = integration_settings.get("meta_access_token", "") or ""
        version = integration_settings.get("meta_graph_api_version", "") or "v20.0"
        self._version = version
        self._base_url = f"{_GRAPH_HOST}/{version}"

    # -- helpers -----------------------------------------------------------

    def _require(self, value: str, name: str) -> str:
        """Devuelve `value` si tiene contenido; si no, MetaConfigError con el
        nombre del setting -- para que el caller reciba "META_AD_ACCOUNT_ID no
        configurado" en vez de un 400 opaco de Meta."""
        if not value:
            raise MetaConfigError(f"{name} no configurado (revisar .env / secret manager).")
        return value

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    @staticmethod
    def _extract_error(resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            return {}
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            return body["error"]
        return {}

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 json: dict | None = None, data: dict | None = None,
                 timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> dict:
        self._require(self._token, "META_ACCESS_TOKEN")
        url = self._url(path)
        try:
            resp = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {self._token}"},
                params=params or None,
                json=json,
                data=data,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            logger.warning("MetaGraphClient: error de red en %s %s | %s", method, path, exc)
            raise MetaApiTransientError(f"Error de red llamando a Meta: {exc}") from exc

        if 200 <= resp.status_code < 300:
            if not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError as exc:
                raise MetaApiError(f"Respuesta de Meta no es JSON valido: {exc}") from exc

        error = self._extract_error(resp)
        code = error.get("code")
        subcode = error.get("error_subcode")
        fbtrace = error.get("fbtrace_id", "")
        message = error.get("message") or resp.text[:300]
        logger.warning(
            "MetaGraphClient: %s %s -> HTTP %s | code=%s subcode=%s fbtrace=%s msg=%s",
            method, path, resp.status_code, code, subcode, fbtrace, message,
        )

        if resp.status_code >= 500:
            raise MetaApiTransientError(f"Meta respondio {resp.status_code}: {message}")
        if resp.status_code == 429 or code in _RATE_LIMIT_CODES:
            raise MetaRateLimitError(f"Rate limit de Meta (code={code}): {message}")
        if resp.status_code in (401, 403) or code in _AUTH_CODES:
            raise MetaAuthError(f"Meta rechazo el token/permiso (code={code}): {message}")
        raise MetaApiError(f"Meta respondio {resp.status_code} (code={code}): {message}")

    # -- API publica -----------------------------------------------------------

    def get(self, path: str, params: dict | None = None,
            timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> dict:
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path: str, json: dict | None = None, data: dict | None = None,
             timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> dict:
        return self._request("POST", path, json=json, data=data, timeout=timeout)

    def delete(self, path: str, params: dict | None = None,
               timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> dict:
        return self._request("DELETE", path, params=params, timeout=timeout)

    def paginate(self, path: str, params: dict | None = None,
                 max_pages: int = _DEFAULT_PAGINATE_MAX_PAGES):
        """
        Generador sobre los items de un edge paginado por cursores. Sigue
        paging.cursors.after hasta que Meta deja de devolver `next`, o hasta
        `max_pages` (tope de seguridad -- nunca un loop infinito si Meta
        devuelve un cursor que no avanza).
        """
        params = dict(params or {})
        seen_pages = 0
        while seen_pages < max_pages:
            page = self._request("GET", path, params=params)
            for item in page.get("data", []):
                yield item
            seen_pages += 1
            paging = page.get("paging") or {}
            after = (paging.get("cursors") or {}).get("after")
            if not after or not paging.get("next"):
                return
            params["after"] = after
