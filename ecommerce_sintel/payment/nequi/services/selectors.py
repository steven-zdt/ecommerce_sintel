from django.core.exceptions import PermissionDenied
from payment.models import NequiTransaction


class NequiSelector:

    @staticmethod
    def get_transaction_by_uuid(tx_uuid: str, user) -> NequiTransaction:
        try:
            tx = NequiTransaction.objects.select_related('order__user').get(uuid=tx_uuid)
        except NequiTransaction.DoesNotExist:
            raise NequiTransaction.DoesNotExist(f"Transaccion no encontrada: {tx_uuid}")

        if tx.order.user != user:
            raise PermissionDenied("No tienes permiso para acceder a esta transaccion.")

        return tx
