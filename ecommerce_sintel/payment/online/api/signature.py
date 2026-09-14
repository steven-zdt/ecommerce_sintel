# Extraido de payment/online/api/views.py -- Sprint 3 (2026-08-05, auditoria
# transversal): _verify_wompi_event_signature es la validacion HMAC del webhook,
# autocontenida y sin relacion con la capa HTTP del ViewSet ni con el fallback de
# reconciliacion (sync.py). Reexportado desde views.py para que los call sites
# existentes (payment/api/views.py, payment/tests.py) sigan importando
# `from payment.online.api.views import _verify_wompi_event_signature` sin cambios.
import hashlib
import hmac
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _verify_wompi_event_signature(payload: dict, request=None) -> bool:
    """
    Valida la autenticidad de un evento Wompi usando el secreto de eventos.

    Algoritmo (doc oficial Wompi):
      1. Extraer el array `properties` del objeto `signature`.
      2. Por cada propiedad, navegar el objeto `data` y concatenar su valor.
      3. Agregar al final `str(timestamp)` y `WOMPI_EVENTS_SECRET`.
      4. SHA256 de la cadena UTF-8 resultante.
      5. Comparar con `signature.checksum` con hmac.compare_digest (timing-safe).
    """
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands

    events_secret: str = getattr(settings, "WOMPI_EVENTS_SECRET", "")
    if not events_secret:
        # Fail-CLOSED: sin el secreto NO se puede verificar la autenticidad del
        # evento, asi que se rechaza. Antes retornaba True (fail-open), lo que
        # permitia falsificar un "pago aprobado" si la variable faltaba en
        # produccion. Ver F-01 de la auditoria.
        logger.critical(
            "Wompi webhook: WOMPI_EVENTS_SECRET no configurado — "
            "evento RECHAZADO (fail-closed)."
        )
        SecurityCommands.log_event(
            SecurityEvent.PAYMENT_WEBHOOK_INVALID_SIGNATURE, request=request, severity=SecurityEvent.SEVERITY_CRITICAL,
            metadata={'reason': 'secret_not_configured'},
        )
        return False

    try:
        sig_obj: dict       = payload.get("signature", {})
        checksum: str       = sig_obj.get("checksum", "")
        properties: list    = sig_obj.get("properties", [])
        timestamp: str|int  = payload.get("timestamp", "")
        data: dict          = payload.get("data", {})

        concatenated = ""
        for prop in properties:
            value: object = data
            for key in prop.split("."):
                value = value.get(key, "") if isinstance(value, dict) else ""
            concatenated += str(value)

        concatenated += str(timestamp) + events_secret
        computed = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

        is_valid = hmac.compare_digest(computed, checksum)
        if not is_valid:
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_WEBHOOK_INVALID_SIGNATURE, request=request, severity=SecurityEvent.SEVERITY_CRITICAL,
                metadata={'event_type': payload.get('event', 'unknown')},
            )
        return is_valid

    except Exception as exc:
        logger.exception("Wompi webhook: error al validar firma | %s", exc)
        return False
