# Extraido de payment/online/api/views.py -- Sprint 3 (2026-08-05, auditoria
# transversal): _sync_wompi_status es el fallback de reconciliacion activa (polling +
# tarea Celery), un bloque autocontenido de logica de sincronizacion, separado de la
# capa HTTP del ViewSet y de la validacion HMAC del webhook. Reexportado desde
# views.py para que los call sites existentes (dashboard/services/admin_orchestrators.py,
# payment/tasks.py, payment/tests.py) sigan importando `from payment.online.api.views
# import _sync_wompi_status` sin cambios.
import logging

import requests as http_requests
from django.conf import settings
from django.db import transaction

from payment.models import Transaction

logger = logging.getLogger(__name__)


def _sync_wompi_status(wompi_tx: Transaction, wompi_id_hint: str = None) -> None:
    """
    Query the Wompi API to sync a PENDING transaction status.
    Called when the user returns from Wompi's confirmation page before
    the webhook has been processed.

    `wompi_id_hint` covers the exact race this function exists for: right after
    the checkout widget closes, Wompi's own webhook (which is the only place that
    normally writes `Transaction.wompi_id`) may not have arrived yet, so
    `wompi_tx.wompi_id` is still None. The widget's own JS callback already knows
    Wompi's transaction id at that point (`result.transaction.id`) -- the frontend
    passes it through as a hint so this function can query Wompi directly instead
    of silently giving up. This is only used to know WHICH transaction to ask
    Wompi about; the actual status always comes from Wompi's API response below,
    never from the hint itself (per Wompi's own guidance: never trust the
    redirect/callback status, only the API/webhook).
    """
    wompi_id = wompi_tx.wompi_id or wompi_id_hint
    if not wompi_id:
        return

    env = getattr(settings, "WOMPI_ENVIRONMENT", "test")
    base_url = (
        "https://sandbox.wompi.co/v1"
        if env != "prod"
        else "https://production.wompi.co/v1"
    )
    private_key = getattr(settings, "WOMPI_PRIVATE_KEY", "")
    if not private_key:
        logger.warning("_sync_wompi_status: WOMPI_PRIVATE_KEY no configurado")
        return

    # Capturado ANTES de cualquier intento (ADR-001 Fase 6): las ramas de error
    # de abajo necesitan el status previo para dejar un TransactionEvent, y
    # wompi_tx.status puede haber sido mutado dentro del bloque atomic si la
    # excepcion ocurre a mitad de camino (el rollback de BD no deshace ese
    # atributo en memoria).
    original_status = wompi_tx.status

    try:
        resp = http_requests.get(
            f"{base_url}/transactions/{wompi_id}",
            headers={"Authorization": f"Bearer {private_key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning(
                "_sync_wompi_status: Wompi respondio %s para wompi_id=%s",
                resp.status_code, wompi_id,
            )
            from payment.online.services.commands import WompiCommands
            WompiCommands.record_sync_event(
                wompi_tx, previous_status=original_status,
                error_detail=f"Wompi respondio {resp.status_code} al consultar wompi_id={wompi_id}",
            )
            return

        data = resp.json().get("data", {})
        new_status = data.get("status", "")
        method_type = data.get("payment_method_type", "")

        # [CORREGIDO 2026-08-04, hallazgo C1 de AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md]:
        # antes de esta validacion, si wompi_tx.wompi_id aun estaba vacio (ventana real: pago
        # recien iniciado, el webhook todavia no llega), esta funcion adoptaba el status de
        # CUALQUIER wompi_id que el cliente pasara por el query param `id`
        # (wompi_id_hint/transaction_status()/confirmation()) sin verificar que perteneciera
        # a esta Transaction -- un usuario autenticado podia tomar el wompi_id de una compra
        # propia ya aprobada y barata para marcar como pagada una Transaction pendiente
        # distinta, de otro monto, sin que existiera un pago real por ese valor. Wompi
        # siempre devuelve en la respuesta el 'reference' y 'amount_in_cents' REALES de la
        # transaccion consultada (los que el comercio envio al crearla, ver
        # WompiCommands.initialize_transaction) -- deben coincidir con los de esta
        # Transaction antes de aceptar cualquier cambio de estado. Nunca se confia en
        # wompi_id_hint como fuente de verdad (ya lo decia el docstring de esta funcion) --
        # ahora tampoco se confia en el resultado de la consulta sin verificar a quien
        # pertenece realmente.
        wompi_reference = data.get("reference", "")
        wompi_amount = data.get("amount_in_cents")
        expected_reference = str(wompi_tx.uuid)
        reference_mismatch = bool(wompi_reference) and wompi_reference != expected_reference
        amount_mismatch = wompi_amount is not None and wompi_amount != wompi_tx.amount_in_cents
        if reference_mismatch or amount_mismatch:
            logger.error(
                "_sync_wompi_status: RECHAZADO -- wompi_id=%s devolvio reference=%s "
                "amount_in_cents=%s, esperado reference=%s amount_in_cents=%s (posible intento "
                "de reconciliar con una transaccion ajena). Ningun cambio aplicado.",
                wompi_id, wompi_reference, wompi_amount, expected_reference, wompi_tx.amount_in_cents,
            )
            from security.models import SecurityEvent
            from security.services.commands import SecurityCommands
            owner = getattr(wompi_tx.order, "user", None) if wompi_tx.order_id else None
            if owner is None and wompi_tx.rental_request_id:
                owner = getattr(wompi_tx.rental_request, "user", None)
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_SYNC_REFERENCE_MISMATCH,
                user=owner, severity=SecurityEvent.SEVERITY_CRITICAL,
                metadata={
                    "transaction_uuid": expected_reference,
                    "wompi_id_queried": wompi_id,
                    "wompi_reference_returned": wompi_reference,
                    "expected_amount_in_cents": wompi_tx.amount_in_cents,
                    "wompi_amount_returned": wompi_amount,
                },
            )
            from payment.online.services.commands import WompiCommands
            WompiCommands.record_sync_event(
                wompi_tx, previous_status=original_status,
                error_detail=f"Mismatch de reference/monto al reconciliar wompi_id={wompi_id}",
            )
            return

        # Se bloquea y guarda una copia separada (no se reasigna wompi_tx: el
        # caller (confirmation()/transaction_status()) mantiene su propia
        # referencia al objeto que le pasamos, y necesita ver los campos
        # actualizados para construir la respuesta -- reasignar el parametro
        # aqui solo actualizaria el nombre local, dejando el objeto del caller
        # con el status viejo en memoria aunque la fila en BD ya cambio).
        with transaction.atomic():
            locked_tx = Transaction.objects.select_for_update().get(pk=wompi_tx.pk)
            update_fields = ["updated_at"]
            previous_status = locked_tx.status

            if not locked_tx.wompi_id:
                locked_tx.wompi_id = wompi_id
                update_fields.append("wompi_id")

            if method_type and method_type != locked_tx.payment_method_type:
                locked_tx.payment_method_type = method_type
                update_fields.append("payment_method_type")

            status_changed = new_status and new_status != locked_tx.status
            if status_changed:
                locked_tx.status = new_status
                update_fields.append("status")

            locked_tx.save(update_fields=update_fields)

            wompi_tx.wompi_id            = locked_tx.wompi_id
            wompi_tx.payment_method_type = locked_tx.payment_method_type
            wompi_tx.status              = locked_tx.status

            if status_changed:
                from payment.online.services.commands import WompiCommands as _WC
                _WC.record_sync_event(
                    locked_tx, previous_status=previous_status,
                    new_status=new_status, raw_payload=data, processed=True,
                )

        if status_changed:
            logger.info(
                "_sync_wompi_status: actualizado corr=%s wompi_id=%s status=%s",
                wompi_tx.correlation_id, wompi_id, new_status,
            )
            from payment.online.services.commands import WompiCommands
            WompiCommands.handle_status_change(wompi_tx, new_status)

    except Exception as exc:
        logger.warning(
            "_sync_wompi_status: error consultando Wompi wompi_id=%s | %s",
            wompi_id, exc,
        )
        from payment.online.services.commands import WompiCommands as _WC
        _WC.record_sync_event(
            wompi_tx, previous_status=original_status,
            error_detail=str(exc)[:500],
        )
