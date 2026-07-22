from django.db import transaction, IntegrityError
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from technical_services.models import (
    TechnicalService, ServiceFAQ, ServiceMarketing, ServiceReview, ServiceOperation,
)


def _toggle_active(instance):
    instance.is_active = not instance.is_active
    instance.save(update_fields=['is_active', 'updated_at'])
    return instance


@transaction.atomic
def _soft_delete(instance) -> None:
    instance.is_deleted = True
    instance.save(update_fields=['is_deleted', 'updated_at'])


def _reorder(model, ordered_uuids: list, **scope) -> None:
    """Reasigna `position` (0..n) segun el orden de `ordered_uuids` (drag&drop).

    Mismo patron que renting/services/catalog.py::_reorder -- ver plan de
    unificacion con Renting.
    """
    items = {
        str(item.uuid): item
        for item in model.objects.filter(is_deleted=False, **scope)
    }
    with transaction.atomic():
        for position, item_uuid in enumerate(ordered_uuids):
            item = items.get(str(item_uuid))
            if item is not None and item.position != position:
                item.position = position
                item.save(update_fields=['position', 'updated_at'])


# ── ServiceFAQ ───────────────────────────────────────────────────────────────

class ServiceFAQSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceFAQ.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceFAQ:
        return get_object_or_404(ServiceFAQ, uuid=uuid, is_deleted=False)


class ServiceFAQCommands:
    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServiceFAQ:
        return ServiceFAQ.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceFAQ, **fields) -> ServiceFAQ:
        allowed = ('question', 'answer', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceFAQ) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceFAQ) -> ServiceFAQ:
        return _toggle_active(instance)

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceFAQ, ordered_uuids, service_id=service_id)


# ── ServiceMarketing ─────────────────────────────────────────────────────────

class ServiceMarketingCommands:
    _ALLOWED_FIELDS = (
        'reference_price', 'promo_price', 'show_discount_percentage', 'tags',
        'main_message', 'featured_benefit', 'trust_message', 'urgency_message',
        'social_proof_message', 'use_cases', 'cta_label',
        'promo_banner_message', 'quick_benefits',
    )

    @staticmethod
    @transaction.atomic
    def upsert(service: TechnicalService, **fields) -> ServiceMarketing:
        marketing, _ = ServiceMarketing.objects.get_or_create(service=service)
        for key, val in fields.items():
            if key in ServiceMarketingCommands._ALLOWED_FIELDS:
                setattr(marketing, key, val)
        marketing.save()
        return marketing

    @staticmethod
    @transaction.atomic
    def delete(service: TechnicalService) -> None:
        ServiceMarketing.objects.filter(service=service, is_deleted=False).update(is_deleted=True)


# ── ServiceReview ────────────────────────────────────────────────────────────

class ServiceReviewSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return (
            ServiceReview.objects
            .filter(service__uuid=service_uuid, is_deleted=False)
            .select_related('user')
            .order_by('-created_at')
        )


class ServiceReviewCommands:
    """Reseñas de servicios. Mismo patron 'ownership + estado terminal' que
    renting.EquipmentReviewCommands.create_review(): se exige que el usuario
    tenga al menos una ServiceOperation en estado CLOSED para el servicio --
    el unique_together del modelo es la segunda capa de defensa contra
    duplicados (carrera).
    """

    @staticmethod
    @transaction.atomic
    def create_review(user, service: TechnicalService, rating: int, comment: str) -> ServiceReview:
        has_closed_operation = ServiceOperation.objects.filter(
            order__user=user,
            order__service_detail__bookings__service_variant__service=service,
            status=ServiceOperation.CLOSED,
        ).exists()
        if not has_closed_operation:
            raise ValueError(
                "Solo puedes calificar servicios que hayas contratado y cuya atencion ya haya finalizado."
            )
        if ServiceReview.objects.filter(user=user, service=service).exists():
            raise ValueError("Ya has calificado este servicio.")

        try:
            return ServiceReview.objects.create(
                user=user, service=service, rating=rating, comment=comment,
            )
        except IntegrityError:
            raise ValueError("Ya has calificado este servicio.")
