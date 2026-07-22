import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SANDBOX_BASE_URL = "https://sandbox.wompi.co/v1"
_PRODUCTION_BASE_URL = "https://production.wompi.co/v1"


class WompiApiError(Exception):
    """Error definitivo (rechazo de negocio, datos invalidos, 4xx) -- no reintentar
    automaticamente, se debe propagar al usuario."""


class WompiApiTransientError(WompiApiError):
    """Error transitorio (timeout, error de red, 5xx) -- seguro de reintentar con backoff."""


class WompiDuplicateReferenceError(WompiApiError):
    """Wompi ya tiene una transaccion creada con esta 'reference' (422, ver docs.wompi.co:
    "reference must be unique per transaction"). No es un fallo del intento actual -- Wompi
    no permite duplicados por diseno (no hay endpoint de busqueda por reference, asi que
    esta excepcion es la unica senal de que ya existe una transaccion previa con este
    reference; el caller debe reconciliar via el wompi_id ya guardado localmente, si lo
    tiene, en vez de reintentar la creacion)."""


class WompiApiClient:
    """
    Cliente HTTP aislado hacia la API de Wompi Colombia. Sin logica de negocio de
    Sintel aqui (nada de Order/Transaction/inventario) -- solo HTTP + serializacion,
    mismo patron que payment/nequi/client.py::NequiApiClient.

    Contrato validado contra docs.wompi.co (2026-07-13), no asumido:
    - POST /payment_sources y POST /transactions usan la LLAVE PRIVADA (Bearer).
    - acceptance_token/accept_personal_auth son JWT presignados con expiracion
      (campo "exp"), obtenidos via GET /merchants/{public_key} (llave publica,
      sin auth de Bearer) -- deben pedirse frescos en CADA creacion de payment_source
      o transaccion, no se obtienen una sola vez y se reusan indefinidamente.
    - La tokenizacion de tarjeta (POST /tokens/cards) NUNCA debe hacerse desde este
      cliente ni desde ningun otro punto del backend -- Wompi exige que los datos de
      tarjeta viajen unicamente entre el navegador del usuario y la API de Wompi,
      nunca por el servidor del comercio. Este cliente no expone ningun metodo de
      tokenizacion a proposito.
    - Wompi NO deduplica por 'reference': reintentar con el mismo reference devuelve
      422 ("Duplicate reference"), nunca la transaccion ya creada.
    """

    def __init__(self):
        env = getattr(settings, "WOMPI_ENVIRONMENT", "test")
        self._base_url = _PRODUCTION_BASE_URL if env == "prod" else _SANDBOX_BASE_URL
        self._public_key = getattr(settings, "WOMPI_PUBLIC_KEY", "")
        self._private_key = getattr(settings, "WOMPI_PRIVATE_KEY", "")

    def _private_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._private_key}"}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = requests.request(method, f"{self._base_url}{path}", timeout=kwargs.pop("timeout", 15), **kwargs)
        except requests.RequestException as exc:
            logger.warning("WompiApiClient: error de red en %s %s | %s", method, path, exc)
            raise WompiApiTransientError(f"Error de red llamando a Wompi: {exc}") from exc

        if resp.status_code >= 500:
            logger.warning("WompiApiClient: %s %s -> %s (transitorio)", method, path, resp.status_code)
            raise WompiApiTransientError(f"Wompi respondio {resp.status_code}")

        if resp.status_code == 422 and self._looks_like_duplicate_reference(resp):
            raise WompiDuplicateReferenceError("Ya existe una transaccion con esta reference en Wompi")

        if resp.status_code >= 400:
            logger.warning("WompiApiClient: %s %s -> %s | body=%s", method, path, resp.status_code, resp.text[:500])
            raise WompiApiError(f"Wompi respondio {resp.status_code}: {resp.text[:300]}")

        try:
            return resp.json()
        except ValueError as exc:
            raise WompiApiError(f"Respuesta de Wompi no es JSON valido: {exc}") from exc

    @staticmethod
    def _looks_like_duplicate_reference(resp) -> bool:
        # El formato exacto del cuerpo de error 422 de Wompi para este caso no esta
        # garantizado por la documentacion consultada -- se hace una deteccion
        # tolerante por texto en vez de asumir una ruta JSON exacta. Verificar y
        # ajustar contra una respuesta real de sandbox antes de depender de esto
        # en un camino critico (ver ADR-001 [VALIDAR EN FASE 2]).
        body = resp.text.lower()
        return "reference" in body and ("duplicate" in body or "unique" in body)

    def get_acceptance_tokens(self) -> dict:
        """
        GET /merchants/{public_key} -- sin autenticacion Bearer (llave publica va en
        la URL). Devuelve acceptance_token (politica de privacidad) y
        accept_personal_auth (tratamiento de datos personales), ambos JWT presignados
        con expiracion -- deben pedirse frescos antes de cada payment_source/transaccion.
        """
        data = self._request("GET", f"/merchants/{self._public_key}")["data"]
        presigned = data.get("presigned_acceptance") or {}
        presigned_personal = data.get("presigned_personal_data_auth") or {}
        acceptance_token = presigned.get("acceptance_token")
        if not acceptance_token:
            raise WompiApiError("Wompi no devolvio acceptance_token en /merchants/{public_key}")
        return {
            "acceptance_token": acceptance_token,
            "accept_personal_auth": presigned_personal.get("acceptance_token"),
        }

    def create_payment_source(self, *, card_token: str, customer_email: str) -> dict:
        """
        POST /payment_sources (llave privada) -- crea una fuente de pago reutilizable
        a partir de un token de tarjeta ya obtenido del lado del cliente (nunca de
        datos de tarjeta crudos). Devuelve el dict 'data' de Wompi, incluyendo 'id'
        (el payment_source_id a guardar en TokenizedCard) y 'status'.
        """
        tokens = self.get_acceptance_tokens()
        payload = {
            "type": "CARD",
            "token": card_token,
            "customer_email": customer_email,
            "acceptance_token": tokens["acceptance_token"],
        }
        if tokens["accept_personal_auth"]:
            payload["accept_personal_auth"] = tokens["accept_personal_auth"]

        data = self._request("POST", "/payment_sources", json=payload, headers=self._private_headers())["data"]
        logger.info("WompiApiClient: payment_source creado | id=%s status=%s", data.get("id"), data.get("status"))
        return data

    def create_transaction(
        self,
        *,
        amount_in_cents: int,
        currency: str,
        reference: str,
        customer_email: str,
        signature: str,
        payment_source_id: int | None = None,
        card_token: str | None = None,
        installments: int = 1,
        redirect_url: str | None = None,
    ) -> dict:
        """
        POST /transactions (llave privada) -- crea la transaccion directamente en
        Wompi desde el backend. Requiere exactamente uno de payment_source_id
        (tarjeta ya guardada) o card_token (tarjeta nueva, recien tokenizada del
        lado del cliente). Devuelve el dict 'data' de Wompi (incluye 'id' = wompi_id
        y 'status' inicial, normalmente PENDING).

        Lanza WompiDuplicateReferenceError si Wompi ya tiene una transaccion con este
        'reference' -- el caller debe tratarlo como "ya se intento antes", nunca como
        un fallo nuevo (ver docstring de la excepcion).
        """
        if (payment_source_id is None) == (card_token is None):
            raise ValueError("Se requiere exactamente uno de payment_source_id o card_token")

        tokens = self.get_acceptance_tokens()
        payload = {
            "amount_in_cents": amount_in_cents,
            "currency": currency,
            "customer_email": customer_email,
            "reference": reference,
            "signature": signature,
            "acceptance_token": tokens["acceptance_token"],
        }
        if tokens["accept_personal_auth"]:
            payload["accept_personal_auth"] = tokens["accept_personal_auth"]

        if payment_source_id is not None:
            payload["payment_source_id"] = payment_source_id
            payload["payment_method"] = {"installments": installments}
        else:
            payload["payment_method"] = {"type": "CARD", "token": card_token, "installments": installments}

        if redirect_url:
            payload["redirect_url"] = redirect_url

        data = self._request("POST", "/transactions", json=payload, headers=self._private_headers())["data"]
        logger.info(
            "WompiApiClient: transaccion creada | reference=%s wompi_id=%s status=%s",
            reference, data.get("id"), data.get("status"),
        )
        return data

    def get_transaction(self, wompi_id: str) -> dict:
        """GET /transactions/{wompi_id} (llave privada) -- consulta el estado actual."""
        return self._request("GET", f"/transactions/{wompi_id}", headers=self._private_headers())["data"]
