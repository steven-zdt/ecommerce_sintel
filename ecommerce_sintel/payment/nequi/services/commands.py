import logging
from decimal import Decimal
from django.db import transaction
from payment.models import NequiTransaction
from payment.nequi.client import NequiApiClient, NequiApiError
from orders.models import Order

logger = logging.getLogger(__name__)


class NequiCommands:

    @staticmethod
    @transaction.atomic
    def initialize_transaction(order: Order, phone_number: str) -> NequiTransaction:
        """Envia pago push Nequi y registra la transaccion vinculada a una Order."""
        amount = Decimal(str(order.total_amount))
        client = NequiApiClient()

        try:
            message_id = client.request_push_payment(
                phone=phone_number,
                amount=amount,
                reference=str(order.uuid),
            )
        except NequiApiError as exc:
            logger.error("Nequi push failed | order=%s phone=%s error=%s", order.uuid, phone_number, exc)
            raise

        nequi_tx = NequiTransaction.objects.create(
            order=order,
            phone_number=phone_number,
            message_id=message_id,
            amount=amount,
            status=NequiTransaction.STATUS_PENDING,
        )
        logger.info("Nequi tx created | tx=%s order=%s message_id=%s", nequi_tx.uuid, order.uuid, message_id)
        return nequi_tx

    @staticmethod
    @transaction.atomic
    def initialize_rental_transaction(rental_request, phone_number: str) -> NequiTransaction:
        """Envia pago push Nequi y registra la transaccion vinculada a una RentalRequest."""
        amount = Decimal(str(rental_request.grand_total))
        client = NequiApiClient()

        try:
            message_id = client.request_push_payment(
                phone=phone_number,
                amount=amount,
                reference=str(rental_request.uuid),
            )
        except NequiApiError as exc:
            logger.error("Nequi push failed | rental=%s phone=%s error=%s", rental_request.uuid, phone_number, exc)
            raise

        nequi_tx = NequiTransaction.objects.create(
            rental_request=rental_request,
            phone_number=phone_number,
            message_id=message_id,
            amount=amount,
            status=NequiTransaction.STATUS_PENDING,
        )
        logger.info("Nequi tx created | tx=%s rental=%s message_id=%s", nequi_tx.uuid, rental_request.uuid, message_id)
        return nequi_tx

    @staticmethod
    @transaction.atomic
    def check_and_update_status(nequi_tx: NequiTransaction) -> NequiTransaction:
        """
        Consulta el estado del pago push en la API de Nequi y actualiza el modelo.
        Si el estado es APPROVED, confirma la Order o la RentalRequest segun corresponda.
        """
        if nequi_tx.status != NequiTransaction.STATUS_PENDING:
            return nequi_tx

        client = NequiApiClient()

        try:
            status = client.get_payment_status(nequi_tx.message_id)
        except NequiApiError as exc:
            logger.error("Nequi status check failed | tx=%s error=%s", nequi_tx.uuid, exc)
            nequi_tx.status = NequiTransaction.STATUS_ERROR
            nequi_tx.save(update_fields=['status'])
            return nequi_tx

        nequi_tx.status = status
        nequi_tx.save(update_fields=['status'])

        if status == NequiTransaction.STATUS_APPROVED:
            if nequi_tx.order_id:
                from payment.shared.commands import confirm_order_payment
                confirm_order_payment(
                    order=nequi_tx.order,
                    reference=f"Nequi {nequi_tx.message_id}",
                )
            elif nequi_tx.rental_request_id:
                from renting.services.commands import RentalRequestCommands
                RentalRequestCommands.confirm_payment(nequi_tx.rental_request)
        elif status in (NequiTransaction.STATUS_REJECTED, NequiTransaction.STATUS_ERROR):
            # El lado 'order' de Nequi rechazado/error no tiene wiring de liberacion
            # hoy tampoco (gap preexistente, fuera de alcance de este cambio) -- solo
            # se libera el lado 'rental_request', que es el que este plan cubre.
            if nequi_tx.rental_request_id:
                from renting.services.commands import RentalRequestCommands
                RentalRequestCommands.release_on_payment_failure(nequi_tx.rental_request)

        return nequi_tx
