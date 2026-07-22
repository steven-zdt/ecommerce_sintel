"""
payment/cards/services/commands.py
Commands for tokenized card management. Extracted from payment/cards/views.py (Sprint 3).
"""
import logging
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from payment.models import TokenizedCard

logger = logging.getLogger(__name__)


class PaymentCardCommands:

    @staticmethod
    @transaction.atomic
    def save_card(user, token_id: str, masked_number: str, brand: str,
                  exp_month: str, exp_year: str, cardholder_name: str = '') -> TokenizedCard:
        """
        Persist a Wompi tokenized card for a user.
        First card is automatically set as default.
        Raises ValueError if token already registered.
        Raises IntegrityError on race condition (handled in view).
        """
        if TokenizedCard.objects.filter(token_id=token_id).exists():
            raise ValueError('Este token ya esta registrado.')

        is_first = not TokenizedCard.objects.filter(user=user, is_deleted=False).exists()
        card = TokenizedCard.objects.create(
            user=user,
            token_id=token_id,
            masked_number=masked_number,
            brand=brand,
            exp_month=exp_month,
            exp_year=exp_year,
            cardholder_name=cardholder_name,
            is_default=is_first,
        )
        logger.info('[cards] Nueva tarjeta tokenizada para %s: %s *%s',
                    user.email, brand, masked_number[-4:])
        return card

    @staticmethod
    @transaction.atomic
    def remove_card(user, card_uuid) -> None:
        """
        Soft-delete a card. If it was the default, promotes the next most recent card.
        """
        card = get_object_or_404(TokenizedCard, uuid=card_uuid, user=user, is_deleted=False)
        was_default = card.is_default
        card.is_deleted = True
        card.is_default = False
        card.save(update_fields=['is_deleted', 'is_default', 'updated_at'])

        if was_default:
            next_card = (
                TokenizedCard.objects
                .filter(user=user, is_deleted=False)
                .order_by('-created_at')
                .first()
            )
            if next_card:
                next_card.is_default = True
                next_card.save(update_fields=['is_default', 'updated_at'])

        return card

    @staticmethod
    @transaction.atomic
    def set_default_card(user, card_uuid) -> TokenizedCard:
        """Mark one card as default, demoting all others for this user."""
        card = get_object_or_404(TokenizedCard, uuid=card_uuid, user=user, is_deleted=False)
        (
            TokenizedCard.objects
            .filter(user=user, is_default=True, is_deleted=False)
            .exclude(pk=card.pk)
            .update(is_default=False)
        )
        card.is_default = True
        card.save(update_fields=['is_default', 'updated_at'])
        return card
