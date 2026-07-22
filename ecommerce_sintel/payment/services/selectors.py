from payment.models import Transaction, CodTransaction, NequiTransaction, TransactionEvent


class PaymentAdminSelector:
    """Lecturas agregadas de las 3 pasarelas de pago para el Panel Admin.
    Cada metodo lista un solo tipo de transaccion -- no se unifican en un
    solo queryset porque Transaction/NequiTransaction/CodTransaction no
    comparten forma (montos en cents vs Decimal, distintos estados)."""

    @staticmethod
    def list_wompi_transactions(status=None):
        qs = Transaction.objects.filter(is_deleted=False).select_related('order', 'rental_request').order_by('-created_at')
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def list_nequi_transactions(status=None):
        qs = NequiTransaction.objects.filter(is_deleted=False).select_related('order', 'rental_request').order_by('-created_at')
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def list_cod_transactions(status=None):
        qs = CodTransaction.objects.filter(is_deleted=False).select_related('order').order_by('-created_at')
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_wompi_transaction(transaction_uuid):
        """ADR-001 Fase 7. Lanza Transaction.DoesNotExist si no existe -- el
        caller (orquestador/vista) decide como responder."""
        return Transaction.objects.select_related('order', 'rental_request').get(
            uuid=transaction_uuid, is_deleted=False,
        )

    @staticmethod
    def list_transaction_events(transaction_uuid):
        """ADR-001 Fase 7: historial append-only visible desde el panel admin."""
        return TransactionEvent.objects.filter(transaction__uuid=transaction_uuid).order_by('-created_at')
