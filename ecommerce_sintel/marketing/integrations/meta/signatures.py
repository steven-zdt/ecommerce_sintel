"""
Verificacion de la firma X-Hub-Signature-256 de los webhooks de Meta.

Funcion pura (sin Django) -- la logica se extrajo de
notifications/api/whatsapp_webhook.py::_signature_valid para poder testearla
aislada y reusarla cuando lleguen otros webhooks de Meta (leads, page, IG).

FAIL-CLOSED: si el app secret esta vacio devuelve False. Nunca abrir el
webhook "temporalmente" -- es la proteccion contra falsificacion de eventos
(mismo fallo F-01 que ya se corrigio una vez en el webhook de Wompi).
"""
import hashlib
import hmac


def verify_meta_webhook_signature(app_secret: str, raw_body: bytes, header_value: str) -> bool:
    """
    Devuelve True solo si `header_value` (contenido del header
    X-Hub-Signature-256, formato "sha256=<hex>") coincide con el HMAC-SHA256
    del cuerpo CRUDO de la request calculado con `app_secret`.

    Debe recibir el body sin parsear (bytes). Una vez que Django/DRF parsea
    request.data ya no se puede volver a leer request.body crudo, asi que el
    caller tiene que leer request.body ANTES de tocar request.data.
    """
    if not app_secret:
        return False
    if not header_value:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        raw_body or b"",
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, header_value)
