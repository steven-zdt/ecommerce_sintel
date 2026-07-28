import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.db import IntegrityError

from payment.models import TokenizedCard
from users.api.permissions import IsAuthenticatedActiveUser
from payment.cards.services.commands import PaymentCardCommands

logger = logging.getLogger(__name__)


class TokenizedCardViewSet(viewsets.ViewSet):
    """
    Gestiona tarjetas tokenizadas del usuario autenticado via Wompi.

    GET    /api/v1/wompi/cards/             - listar tarjetas guardadas
    POST   /api/v1/wompi/cards/             - guardar token recibido de Wompi.js
    DELETE /api/v1/wompi/cards/{uuid}/      - eliminar tarjeta (soft-delete)
    POST   /api/v1/wompi/cards/{uuid}/set-default/ - marcar como predeterminada
    """
    permission_classes = [IsAuthenticatedActiveUser]
    lookup_field = 'uuid'

    # F-03 (auditoria enterprise): solo `create` (tokenizar una tarjeta)
    # necesita limite de tasa -- es el punto con riesgo real de abuso
    # (probar numeros de tarjeta robados, "carding").
    ACTION_THROTTLE_SCOPES = {'create': 'payment_card_create'}

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    def list(self, request):
        cards = (
            TokenizedCard.objects
            .filter(user=request.user, is_deleted=False)
            .order_by('-is_default', '-created_at')
        )
        data = [_serialize_card(c) for c in cards]
        return Response(data)

    def create(self, request):
        token_id = request.data.get('token_id', '').strip()
        masked_number = request.data.get('masked_number', '').strip()
        brand = request.data.get('brand', '').strip()
        exp_month = request.data.get('exp_month', '').strip()
        exp_year = request.data.get('exp_year', '').strip()
        cardholder_name = request.data.get('cardholder_name', '').strip()

        if not all([token_id, masked_number, brand, exp_month, exp_year]):
            return Response(
                {'detail': 'token_id, masked_number, brand, exp_month y exp_year son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            card = PaymentCardCommands.save_card(
                user=request.user,
                token_id=token_id,
                masked_number=masked_number,
                brand=brand,
                exp_month=exp_month,
                exp_year=exp_year,
                cardholder_name=cardholder_name,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except IntegrityError:
            # Race condition: two simultaneous creations for a user with no cards
            return Response(
                {'detail': 'Ya existe una tarjeta predeterminada, intenta de nuevo.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(_serialize_card(card), status=status.HTTP_201_CREATED)

    def destroy(self, request, uuid=None):
        card = PaymentCardCommands.remove_card(user=request.user, card_uuid=uuid)

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.PAYMENT_CARD_REMOVED, request=request, user=request.user,
            metadata={'card_uuid': str(card.uuid)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        try:
            card = PaymentCardCommands.set_default_card(user=request.user, card_uuid=uuid)
        except IntegrityError:
            return Response(
                {'detail': 'No se pudo actualizar la tarjeta predeterminada, intenta de nuevo.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(_serialize_card(card))


def _serialize_card(card: TokenizedCard) -> dict:
    return {
        'uuid': str(card.uuid),
        # Bug real preexistente (auditoria E2E, 2026-07-22): faltaba aqui pese a
        # que el modelo si lo tiene -- el frontend siempre referencio
        # `card.token_id` (initialize/ necesita el token_id real de Wompi para
        # cobrar una tarjeta guardada, no el uuid interno), asi que toda
        # seleccion de tarjeta guardada resolvia a `undefined`, y initialize/
        # terminaba sin campo card_token -- silenciosamente caia al flujo
        # Widget en vez de cobrar la tarjeta guardada elegida.
        'token_id': card.token_id,
        'brand': card.brand,
        'masked_number': card.masked_number,
        'exp_month': card.exp_month,
        'exp_year': card.exp_year,
        'cardholder_name': card.cardholder_name,
        'is_default': card.is_default,
        'created_at': card.created_at.isoformat(),
    }
