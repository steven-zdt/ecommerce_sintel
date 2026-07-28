import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import GenericViewSet
from users.api.permissions import IsAuthenticatedActiveUser
from orders.models import Order
from payment.models import NequiTransaction
from payment.nequi.client import NequiApiError
from payment.nequi.services.commands import NequiCommands
from payment.nequi.services.selectors import NequiSelector
from payment.nequi.api.serializers import NequiInitializeSerializer, NequiTransactionSerializer

logger = logging.getLogger(__name__)


class NequiPaymentViewSet(GenericViewSet):
    permission_classes = [IsAuthenticatedActiveUser]

    # F-03 (auditoria enterprise): initialize() dispara un push real a Nequi
    # (costo por intento) sin ningun limite de tasa.
    ACTION_THROTTLE_SCOPES = {'initialize': 'payment_nequi_initialize'}

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    @action(detail=False, methods=['post'], url_path='initialize')
    def initialize(self, request):
        """
        Inicia un pago push Nequi para una orden pendiente.
        POST /api/v1/wompi/nequi/initialize/
        Body: { order_uuid, phone_number }
        """
        serializer = NequiInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order = Order.objects.get(uuid=data['order_uuid'])
        except Order.DoesNotExist:
            return Response({'detail': 'Orden no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if order.user != request.user:
            return Response({'detail': 'No tienes permiso sobre esta orden.'}, status=status.HTTP_403_FORBIDDEN)

        if order.status != Order.STATUS_PENDING_PAYMENT:
            return Response({'detail': 'La orden no esta en estado pendiente.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nequi_tx = NequiCommands.initialize_transaction(
                order=order,
                phone_number=data['phone_number'],
            )
        except NequiApiError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(NequiTransactionSerializer(nequi_tx).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='status')
    def check_status(self, request):
        """
        Consulta y actualiza el estado de una transaccion Nequi.
        GET /api/v1/wompi/nequi/status/?tx=<uuid>
        """
        tx_uuid = request.query_params.get('tx')
        if not tx_uuid:
            return Response({'detail': 'Parametro tx requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nequi_tx = NequiSelector.get_transaction_by_uuid(tx_uuid, request.user)
        except NequiTransaction.DoesNotExist:
            return Response({'detail': 'Transaccion no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError:
            return Response({'detail': 'No tienes permiso sobre esta transaccion.'}, status=status.HTTP_403_FORBIDDEN)

        if nequi_tx.status == NequiTransaction.STATUS_PENDING:
            nequi_tx = NequiCommands.check_and_update_status(nequi_tx)

        return Response(NequiTransactionSerializer(nequi_tx).data)
