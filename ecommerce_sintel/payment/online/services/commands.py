import hashlib
import logging
import uuid as uuid_lib
from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from django.conf import settings
from payment.models import Transaction, TransactionEvent
from orders.models import Order
from payment.shared.commands import confirm_order_payment, _get_stock_record
from payment.online.wompi_client import WompiApiClient, WompiApiError
from inventory.services.selectors import InventorySelector

logger = logging.getLogger(__name__)


def _has_sufficient_stock(variant, quantity: int) -> bool:
    record = _get_stock_record(variant)
    if record is None:
        return False
    return InventorySelector.get_current_stock(record.id) >= quantity


def _compute_integrity_signature(reference: str, amount_in_cents: int, currency: str) -> str:
    secret = settings.WOMPI_INTEGRITY_SECRET
    raw = f"{reference}{amount_in_cents}{currency}{secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class WompiCommands:

    @staticmethod
    def initialize_transaction(
        order: Order = None, rental_request=None, *,
        card_token: str = None, payment_source_id: int = None, correlation_id: str = None,
    ) -> Transaction:
        """
        Crea una Transaction PENDING para una Order o una RentalRequest (excluyentes).

        `card_token`/`payment_source_id` son OPCIONALES y mutuamente excluyentes
        (ADR-001, payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md, Sec.4): si se
        pasa alguno, la transaccion se crea tambien de forma SINCRONA en Wompi via
        WompiApiClient, y wompi_id/status quedan disponibles de inmediato sin
        depender del webhook. Si no se pasa ninguno -- el unico camino usado por
        PSE/Otros (ver CheckoutView.vue, el Widget completo sigue abriendose ahi) --
        el comportamiento es IDENTICO al de siempre: solo se crea la Transaction
        local con su firma de integridad, y es el Widget quien crea la transaccion
        del lado de Wompi.

        `correlation_id` (ADR-001 Fase 4, observabilidad): identifica este intento
        de pago end-to-end (creacion, sync por polling, webhook) en los logs y en
        TransactionEvent. Si no se pasa uno (llamadores existentes antes de esta
        fase), se minta aqui mismo -- nunca queda vacio.
        """
        if not order and not rental_request:
            raise ValueError("Se requiere order o rental_request para iniciar la transaccion.")
        if card_token and payment_source_id:
            raise ValueError("Se requiere card_token o payment_source_id, no ambos.")

        correlation_id = correlation_id or str(uuid_lib.uuid4())

        total = order.total_amount if order else rental_request.grand_total
        total_decimal   = Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        amount_in_cents = int(total_decimal * 100)
        currency        = "COP"

        # Atomico solo hasta aqui (creacion + firma): si `_create_transaction_sync`
        # falla mas abajo, marca la Transaction como ERROR y crea su TransactionEvent
        # de auditoria y vuelve a lanzar -- eso NO debe hacer rollback de la creacion
        # ya confirmada ni de su propio registro de error, asi que corre fuera de
        # este bloque atomico (antes vivia todo junto bajo un solo @transaction.atomic
        # en el metodo completo, y el `raise` en el except de mas abajo deshacia
        # tambien el status=ERROR/TransactionEvent que se acababa de guardar).
        with transaction.atomic():
            # Order.payment_method debe reflejar el metodo realmente elegido, no
            # el default del modelo (bug real: en Servicios Tecnicos la Order se
            # crea ANTES de elegir metodo de pago, asi que payment_method llegaba
            # aqui todavia en su default 'WOMPI' -- fijarlo explicitamente hace
            # que sea correcto por diseno y no por coincidencia con ese default).
            if order and order.payment_method != 'WOMPI':
                order.payment_method = 'WOMPI'
                order.save(update_fields=['payment_method'])

            wompi_tx = Transaction.objects.create(
                order=order,
                rental_request=rental_request,
                amount_in_cents=amount_in_cents,
                currency=currency,
                status="PENDING",
                correlation_id=correlation_id,
                initiation_channel=(
                    Transaction.CHANNEL_CARD_API if (card_token or payment_source_id)
                    else Transaction.CHANNEL_WIDGET
                ),
            )
            wompi_tx.integrity_signature = _compute_integrity_signature(
                reference=str(wompi_tx.uuid),
                amount_in_cents=amount_in_cents,
                currency=currency,
            )
            wompi_tx.save(update_fields=["integrity_signature"])

        logger.info(
            "Wompi transaction initialized | corr=%s order=%s rental_request=%s tx=%s amount_cents=%s",
            correlation_id, order.uuid if order else None,
            rental_request.uuid if rental_request else None,
            wompi_tx.uuid, amount_in_cents,
        )

        if card_token or payment_source_id:
            WompiCommands._create_transaction_sync(
                wompi_tx, order, rental_request, card_token, payment_source_id,
            )

        return wompi_tx

    @staticmethod
    def _create_transaction_sync(
        wompi_tx: Transaction, order, rental_request, card_token, payment_source_id,
    ) -> None:
        """
        Crea la transaccion directamente en Wompi desde el backend (ADR-001 Sec.4).
        Alcanzable desde CheckoutView.vue sub-metodo "Tarjeta" (Fase 3b) -- PSE/Otros
        sigue sin pasar por aqui, usa el Widget completo como siempre.
        """
        user = order.user if order else rental_request.user
        client = WompiApiClient()
        previous_status = wompi_tx.status
        try:
            data = client.create_transaction(
                amount_in_cents=wompi_tx.amount_in_cents,
                currency=wompi_tx.currency,
                reference=str(wompi_tx.uuid),
                customer_email=user.email,
                signature=wompi_tx.integrity_signature,
                payment_source_id=payment_source_id,
                card_token=card_token,
            )
        except WompiApiError as exc:
            # reference es un uuid recien generado en este mismo metodo, asi que
            # una WompiDuplicateReferenceError aqui seria una colision practicamente
            # imposible -- se trata igual que cualquier otro fallo de creacion.
            wompi_tx.status = "ERROR"
            wompi_tx.save(update_fields=["status", "updated_at"])
            TransactionEvent.objects.create(
                transaction=wompi_tx, source=TransactionEvent.SOURCE_API_CREATE,
                previous_status=previous_status, new_status="ERROR",
                correlation_id=wompi_tx.correlation_id, processed=False, error_detail=str(exc),
            )
            logger.error(
                "WompiCommands: fallo al crear transaccion sincrona en Wompi | corr=%s tx=%s | %s",
                wompi_tx.correlation_id, wompi_tx.uuid, exc,
            )
            raise

        wompi_tx.wompi_id = str(data.get("id", ""))
        wompi_tx.status = data.get("status") or wompi_tx.status
        method_type = data.get("payment_method_type") or (data.get("payment_method") or {}).get("type", "")
        if method_type:
            wompi_tx.payment_method_type = method_type
        wompi_tx.save(update_fields=["wompi_id", "status", "payment_method_type", "updated_at"])

        TransactionEvent.objects.create(
            transaction=wompi_tx, source=TransactionEvent.SOURCE_API_CREATE,
            previous_status=previous_status, new_status=wompi_tx.status,
            correlation_id=wompi_tx.correlation_id, raw_payload=data, processed=True,
        )

        logger.info(
            "WompiCommands: transaccion creada sincronamente en Wompi | corr=%s tx=%s wompi_id=%s status=%s",
            wompi_tx.correlation_id, wompi_tx.uuid, wompi_tx.wompi_id, wompi_tx.status,
        )

        if wompi_tx.status == "APPROVED":
            PaymentCommands.confirm_payment(wompi_tx)

    @staticmethod
    def record_sync_event(
        wompi_tx: Transaction,
        previous_status: str,
        new_status: str = "",
        raw_payload: dict = None,
        processed: bool = False,
        error_detail: str = "",
    ) -> TransactionEvent:
        """
        Persist a TransactionEvent for the API-sync path (_sync_wompi_status).
        Centralises all SOURCE_API_SYNC creates that were previously inline in views.py.
        """
        return TransactionEvent.objects.create(
            transaction=wompi_tx,
            source=TransactionEvent.SOURCE_API_SYNC,
            previous_status=previous_status,
            new_status=new_status,
            correlation_id=wompi_tx.correlation_id,
            raw_payload=raw_payload or {},
            processed=processed,
            error_detail=error_detail,
        )

    @staticmethod
    def handle_status_change(wompi_tx: Transaction, new_status: str) -> None:
        """
        Que hacer cuando el status de una Transaction Wompi cambia a un estado
        terminal -- extraido (2026-07-14) para que el webhook real
        (process_webhook_notification) y el fallback de reconciliacion
        (_sync_wompi_status en payment/online/api/views.py, usado por el polling
        de PaymentResultView Y por la tarea periodica
        payment.tasks.reconcile_pending_wompi_transactions) mantengan
        RentalRequest/Order sincronizados con Wompi de la misma forma. Antes de
        este cambio, _sync_wompi_status solo manejaba APPROVED: si el webhook se
        perdia/retrasaba y la reconciliacion descubria un DECLINED/VOIDED/FAILED,
        la Transaction se actualizaba pero el RentalRequest/Order asociado se
        quedaba huerfano en pending_payment -- discrepancia real entre el estado
        de Wompi y el de la solicitud.
        """
        if new_status == "APPROVED":
            PaymentCommands.confirm_payment(wompi_tx)
        elif new_status in ("DECLINED", "VOIDED", "ERROR", "FAILED"):
            from security.models import SecurityEvent
            from security.services.commands import SecurityCommands
            owner = getattr(wompi_tx.order, 'user', None) or getattr(wompi_tx.rental_request, 'user', None)
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_DECLINED, user=owner, severity=SecurityEvent.SEVERITY_WARNING,
                metadata={
                    'reference': str(wompi_tx.uuid), 'status': new_status,
                    'correlation_id': wompi_tx.correlation_id,
                },
            )
            if wompi_tx.rental_request_id:
                from renting.services.commands import RentalRequestCommands
                RentalRequestCommands.release_on_payment_failure(wompi_tx.rental_request)
            else:
                from technical_services.services.commands import ServiceCommands
                ServiceCommands.release_slot_on_failure(wompi_tx.order)

    @staticmethod
    def process_webhook_notification(payload: dict) -> None:
        # Auditoria completa del evento recibido (Fase 10): antes solo se logueaba
        # el payload completo cuando la firma era invalida; un evento valido con
        # datos inesperados no dejaba rastro.
        logger.info("Wompi webhook payload | %s", str(payload)[:1000])

        event_data: dict = payload.get("data", {}).get("transaction", {})
        reference: str   = event_data.get("reference", "")
        new_status: str  = event_data.get("status", "")
        wompi_id: str    = event_data.get("id", "")

        if not reference:
            logger.warning("Wompi webhook: payload sin campo 'reference'.")
            return

        # select_for_update() serializa entregas concurrentes del mismo webhook
        # (Wompi reintenta en caso de timeout/error de red) para la misma
        # Transaction -- sin este lock, dos entregas simultaneas podrian ambas
        # leer el status previo antes de que cualquiera escriba, evadiendo el
        # guard de idempotencia de abajo (que solo compara contra el valor ya
        # guardado en BD).
        with transaction.atomic():
            try:
                wompi_tx = Transaction.objects.select_for_update().get(uuid=reference)
            except Transaction.DoesNotExist:
                logger.warning("Wompi webhook: transaccion no encontrada | reference=%s", reference)
                return

            correlation_id  = wompi_tx.correlation_id
            previous_status = wompi_tx.status
            if previous_status == "APPROVED" and new_status == "APPROVED":
                logger.info(
                    "Wompi webhook duplicado ignorado | corr=%s reference=%s wompi_id=%s",
                    correlation_id, reference, wompi_id,
                )
                TransactionEvent.objects.create(
                    transaction=wompi_tx, source=TransactionEvent.SOURCE_WEBHOOK,
                    previous_status=previous_status, new_status=new_status,
                    correlation_id=correlation_id, raw_payload=payload,
                    processed=False, error_detail="Webhook duplicado ignorado (idempotencia).",
                )
                return

            wompi_tx.status   = new_status
            wompi_tx.wompi_id = wompi_id
            wompi_tx.save(update_fields=["status", "wompi_id", "updated_at"])

            TransactionEvent.objects.create(
                transaction=wompi_tx, source=TransactionEvent.SOURCE_WEBHOOK,
                previous_status=previous_status, new_status=new_status,
                correlation_id=correlation_id, raw_payload=payload, processed=True,
            )

        logger.info(
            "Wompi webhook procesado | corr=%s reference=%s status=%s wompi_id=%s",
            correlation_id, reference, new_status, wompi_id,
        )

        WompiCommands.handle_status_change(wompi_tx, new_status)


class PaymentCommands:

    @staticmethod
    def confirm_payment(wompi_transaction: Transaction) -> None:
        if wompi_transaction.status != "APPROVED":
            return

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands

        if wompi_transaction.rental_request_id:
            from renting.services.commands import RentalRequestCommands
            RentalRequestCommands.confirm_payment(wompi_transaction.rental_request)
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_APPROVED, user=wompi_transaction.rental_request.user,
                severity=SecurityEvent.SEVERITY_INFO,
                metadata={
                    'wompi_id': wompi_transaction.wompi_id,
                    'correlation_id': wompi_transaction.correlation_id,
                    'rental_request': str(wompi_transaction.rental_request.uuid),
                },
            )
            return

        order = wompi_transaction.order
        insufficient_item = None

        with transaction.atomic():
            for item in order.items.select_for_update().all():
                variant = item.variant or item.equipment_variant
                if variant and not _has_sufficient_stock(variant, item.quantity):
                    insufficient_item = item
                    break

        if insufficient_item is not None:
            # Guardado fuera del bloque atomic anterior: si estuviera dentro, el
            # raise siguiente revertiria este mismo save junto con la excepcion,
            # dejando la Transaction como 'APPROVED' en BD pese al error (bug real
            # detectado el 2026-07-03, ver ARQUITECTURA_COMPLETA_PAYMENT.md).
            wompi_transaction.status = "ERROR"
            wompi_transaction.save(update_fields=["status", "updated_at"])
            logger.error(
                "confirm_payment: stock insuficiente | order=%s item=%s",
                order.uuid, insufficient_item.sku,
            )
            raise ValueError(f"Stock insuficiente para {insufficient_item.item_name} al confirmar el pago.")

        confirm_order_payment(
            order=order,
            reference=f"Wompi {wompi_transaction.wompi_id}",
        )
        SecurityCommands.log_event(
            SecurityEvent.PAYMENT_APPROVED, user=order.user, severity=SecurityEvent.SEVERITY_INFO,
            metadata={
                'wompi_id': wompi_transaction.wompi_id,
                'correlation_id': wompi_transaction.correlation_id,
                'order': str(order.uuid),
            },
        )
