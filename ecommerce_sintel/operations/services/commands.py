import logging
import uuid
from django.db import transaction
from django.utils import timezone

from operations.models import (
    OperationTicket, OperationAssignment, TrackingEvent,
    OperationDocument, OperationReview, DispatcherProfile,
)
from operations.services.config import (
    ALLOWED_TRANSITIONS, CUSTOMER_REQUIRED_DOCS, STATUS_TO_MILESTONE,
)

logger = logging.getLogger(__name__)


def _generate_ticket_number() -> str:
    from django.utils import timezone as tz
    year = tz.now().year
    return f"OP-{year}-{uuid.uuid4().hex[:8].upper()}"


class OperationCommands:

    @staticmethod
    @transaction.atomic
    def ensure_tickets_for_order(order) -> list[OperationTicket]:
        """
        Crea un ticket por tipo de item de la orden.
        Es idempotente por la restriccion (source_order, operation_type).
        """
        item_types = []
        if order.items.filter(variant__isnull=False).exists():
            item_types.append(OperationTicket.SHOP_DELIVERY)
        if order.items.filter(equipment_variant__isnull=False).exists():
            item_types.append(OperationTicket.RENTAL)
        if order.items.filter(service_variant__isnull=False).exists():
            item_types.append(OperationTicket.SERVICE)
        if not item_types:
            item_types.append(OperationTicket.SHOP_DELIVERY)

        tickets = []
        for operation_type in item_types:
            ticket = OperationTicket.objects.filter(
                source_order=order,
                operation_type=operation_type,
                is_deleted=False,
            ).first()
            if ticket is None:
                ticket = OperationCommands._create_ticket_for_order(order, operation_type)
            tickets.append(ticket)
        return tickets

    @staticmethod
    @transaction.atomic
    def ensure_ticket_for_order(order) -> OperationTicket:
        """Alias compatible; retorna el primer ticket generado para la orden."""
        return OperationCommands.ensure_tickets_for_order(order)[0]

    @staticmethod
    def _create_ticket_for_order(order, operation_type: str) -> OperationTicket:
        customer_docs = CUSTOMER_REQUIRED_DOCS.get(operation_type, [])
        initial_status = (
            OperationTicket.STATUS_DOCS_PENDING
            if customer_docs
            else OperationTicket.STATUS_READY
        )
        address_obj = getattr(order, 'shipping_address', None)
        ticket = OperationTicket.objects.create(
            ticket_number=_generate_ticket_number(),
            operation_type=operation_type,
            status=initial_status,
            customer=order.user,
            source_order=order,
            location_address=getattr(address_obj, 'address_line_1', '') if address_obj else '',
            location_city=getattr(address_obj, 'city', '') if address_obj else '',
            location_department=getattr(address_obj, 'state', '') if address_obj else '',
        )
        TrackingEvent.objects.create(
            ticket=ticket,
            milestone=TrackingEvent.MILESTONE_CREATED,
            description='Ticket creado automaticamente tras confirmacion de pago.',
        )
        if operation_type == OperationTicket.SHOP_DELIVERY:
            OperationCommands._generate_invoice_doc(ticket, order)

        user = order.user
        ticket_uuid = str(ticket.uuid)
        ticket_number = ticket.ticket_number
        transaction.on_commit(
            lambda: _dispatch(
                user=user,
                slug='operation_created',
                context={
                    'ticket_number': ticket_number,
                    'ticket_uuid': ticket_uuid,
                    'operation_type': operation_type,
                },
            )
        )
        logger.info("OperationTicket creado | ticket=%s order=%s", ticket.uuid, order.uuid)
        return ticket

    @staticmethod
    @transaction.atomic
    def ensure_ticket_for_rental(rental_request) -> OperationTicket:
        """
        Crea (o recupera) el ticket de operacion vinculado a una RentalRequest pagada.
        Idempotente.
        """
        existing = OperationTicket.objects.filter(
            source_rental_request=rental_request, is_deleted=False
        ).first()
        if existing:
            return existing

        customer_docs = CUSTOMER_REQUIRED_DOCS.get(OperationTicket.RENTAL, [])
        initial_status = (
            OperationTicket.STATUS_DOCS_PENDING
            if customer_docs
            else OperationTicket.STATUS_READY
        )

        priority = getattr(rental_request, 'priority', OperationTicket.PRIORITY_LOW)
        if priority not in (OperationTicket.PRIORITY_HIGH, OperationTicket.PRIORITY_LOW):
            priority = OperationTicket.PRIORITY_LOW

        ticket = OperationTicket.objects.create(
            ticket_number=_generate_ticket_number(),
            operation_type=OperationTicket.RENTAL,
            status=initial_status,
            priority=priority,
            customer=rental_request.user,
            source_rental_request=rental_request,
            location_address=getattr(rental_request, 'location_address', ''),
            location_city=getattr(rental_request, 'location_city', ''),
            location_department=getattr(rental_request, 'location_department', ''),
        )

        TrackingEvent.objects.create(
            ticket=ticket,
            milestone=TrackingEvent.MILESTONE_CREATED,
            description='Ticket creado automaticamente tras confirmacion de pago de alquiler.',
        )

        _user = rental_request.user
        _uuid = str(ticket.uuid)
        _num  = ticket.ticket_number
        transaction.on_commit(
            lambda: _dispatch(
                user=_user,
                slug='operation_created',
                context={
                    'ticket_number': _num,
                    'ticket_uuid':   _uuid,
                    'operation_type': OperationTicket.RENTAL,
                },
            )
        )

        logger.info(
            "OperationTicket (RENTAL) creado | ticket=%s rental_request=%s",
            ticket.uuid, rental_request.uuid,
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def assign_resource(
        ticket: OperationTicket,
        assignee,
        role: str,
        assigned_by=None,
        slot=None,
    ) -> OperationAssignment:
        ticket = OperationTicket.objects.select_for_update().get(pk=ticket.pk)
        if ticket.status not in (
            OperationTicket.STATUS_CREATED,
            OperationTicket.STATUS_DOCS_PENDING,
            OperationTicket.STATUS_READY,
            OperationTicket.STATUS_ASSIGNED,
        ):
            raise ValueError("El ticket no admite asignaciones en su estado actual.")

        if OperationAssignment.objects.filter(
            ticket=ticket,
            role=role,
            status=OperationAssignment.STATUS_ACTIVE,
            is_deleted=False,
        ).exists():
            raise ValueError("El ticket ya tiene una asignacion activa para este rol.")

        if role in (
            OperationAssignment.ROLE_DISPATCHER,
            OperationAssignment.ROLE_TRANSPORTER,
        ):
            dp = DispatcherProfile.objects.select_for_update().filter(
                user=assignee, is_deleted=False
            ).first()
            if not dp or not dp.is_available or not dp.is_active:
                raise ValueError("El transportista no esta disponible.")
            dp.is_available = False
            dp.save(update_fields=['is_available', 'updated_at'])

        if role == OperationAssignment.ROLE_TECHNICIAN:
            from accounts.models import TechnicianProfile
            technician = TechnicianProfile.objects.select_for_update().filter(
                user=assignee, is_deleted=False
            ).first()
            if not technician or not technician.is_available:
                raise ValueError("El tecnico no esta disponible.")
            technician.is_available = False
            technician.save(update_fields=['is_available', 'updated_at'])

        if role == OperationAssignment.ROLE_CONTRACTOR:
            from accounts.services.profile_resolver import ProfileResolver
            from accounts.services.profile_registry import CONTRACTOR_ASSIGNABLE_TYPES
            is_contractor_profile = ProfileResolver.has_type(assignee, CONTRACTOR_ASSIGNABLE_TYPES)
            dispatcher = ProfileResolver.get_dispatcher_profile(assignee)
            is_field_ops_dispatcher = dispatcher is not None and dispatcher.dispatcher_type == DispatcherProfile.FIELD_OPS
            if not (is_contractor_profile or is_field_ops_dispatcher):
                raise ValueError("El usuario no tiene un perfil de contratista.")

        assignment = OperationAssignment.objects.create(
            ticket=ticket,
            assignee=assignee,
            role=role,
            assigned_by=assigned_by,
            availability_slot=slot,
        )

        if ticket.status in (OperationTicket.STATUS_CREATED, OperationTicket.STATUS_READY):
            OperationCommands._transition(ticket, OperationTicket.STATUS_ASSIGNED, by=assigned_by)

        _user = ticket.customer
        _num  = ticket.ticket_number
        _assignee_name = getattr(assignee, 'get_short_name', lambda: assignee.email)()
        transaction.on_commit(
            lambda: _dispatch(
                user=_user,
                slug='operation_assigned',
                context={
                    'ticket_number': _num,
                    'assignee_name': _assignee_name,
                    'role': role,
                },
            )
        )

        logger.info(
            "Asignacion creada | ticket=%s assignee=%s role=%s",
            ticket.uuid, assignee.pk, role,
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def auto_assign(ticket: OperationTicket, assigned_by=None) -> OperationAssignment:
        if ticket.operation_type == OperationTicket.SERVICE:
            from technical_services.services.selectors import TechnicianSelector
            order = ticket.source_order
            category = None
            if order:
                svc_item = order.items.filter(service_variant__isnull=False).first()
                if svc_item and svc_item.service_variant:
                    category = svc_item.service_variant.service.category

            if category is None:
                raise ValueError("No se pudo determinar la categoria para auto-asignacion.")

            technicians = TechnicianSelector.get_available_for_category(category)
            if not technicians.exists():
                raise ValueError("No hay tecnicos disponibles para esta categoria.")
            assignee = technicians.first().user
            role = OperationAssignment.ROLE_TECHNICIAN

        else:
            from operations.services.selectors import DispatcherSelector
            candidates = DispatcherSelector.get_available(
                city=ticket.location_city,
                date=ticket.scheduled_date,
            )
            if not candidates.exists():
                raise ValueError("No hay despachadores disponibles para esta ciudad.")
            assignee = candidates.first().user
            role = OperationAssignment.ROLE_DISPATCHER

        return OperationCommands.assign_resource(
            ticket=ticket,
            assignee=assignee,
            role=role,
            assigned_by=assigned_by,
        )

    @staticmethod
    @transaction.atomic
    def schedule(ticket: OperationTicket, date, start_time, end_time, by=None) -> OperationTicket:
        ticket = OperationTicket.objects.select_for_update().get(pk=ticket.pk)
        if ticket.status != OperationTicket.STATUS_ASSIGNED:
            raise ValueError("Solo se puede programar un ticket asignado.")
        ticket.scheduled_date       = date
        ticket.scheduled_time_start = start_time
        ticket.scheduled_time_end   = end_time
        ticket.save(update_fields=['scheduled_date', 'scheduled_time_start', 'scheduled_time_end', 'updated_at'])

        OperationCommands._transition(ticket, OperationTicket.STATUS_SCHEDULED, by=by)

        _user = ticket.customer
        _num  = ticket.ticket_number
        _date = str(date)
        transaction.on_commit(
            lambda: _dispatch(
                user=_user,
                slug='operation_scheduled',
                context={'ticket_number': _num, 'scheduled_date': _date},
            )
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def transition_status(
        ticket: OperationTicket,
        new_status: str,
        by=None,
        note: str = '',
    ) -> OperationTicket:
        ticket = OperationTicket.objects.select_for_update().get(pk=ticket.pk)
        previous_status = ticket.status
        allowed = ALLOWED_TRANSITIONS.get(previous_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Transicion invalida: {ticket.status} -> {new_status}. "
                f"Permitidas: {allowed}"
            )

        OperationCommands._transition(ticket, new_status, by=by, note=note)

        if new_status == OperationTicket.STATUS_CANCELLED:
            from security.models import SecurityEvent
            from security.services.commands import SecurityCommands
            SecurityCommands.log_event(
                SecurityEvent.OPERATION_FORCE_CANCELLED, user=by, severity=SecurityEvent.SEVERITY_WARNING,
                metadata={'ticket': ticket.ticket_number, 'previous_status': previous_status},
            )

        if new_status in (OperationTicket.STATUS_COMPLETED, OperationTicket.STATUS_CANCELLED) or (
            previous_status == OperationTicket.STATUS_ASSIGNED
            and new_status == OperationTicket.STATUS_READY
        ):
            OperationCommands._release_assignments(ticket)
        if new_status == OperationTicket.STATUS_COMPLETED:
            OperationCommands._on_completed(ticket)

        slug = _status_notification_slug(new_status)
        if slug:
            _user = ticket.customer
            _num  = ticket.ticket_number
            transaction.on_commit(
                lambda: _dispatch(
                    user=_user,
                    slug=slug,
                    context={'ticket_number': _num, 'status': new_status},
                )
            )

        return ticket

    @staticmethod
    def _transition(ticket: OperationTicket, new_status: str, by=None, note: str = '') -> None:
        ticket.status = new_status
        ticket.save(update_fields=['status', 'updated_at'])

        milestone = STATUS_TO_MILESTONE.get(new_status)
        if milestone:
            TrackingEvent.objects.create(
                ticket=ticket,
                milestone=milestone,
                description=note,
                created_by=by,
            )

    @staticmethod
    def _on_completed(ticket: OperationTicket) -> None:
        if ticket.operation_type == OperationTicket.RENTAL and ticket.source_rental_request:
            from renting.services.commands import RentalRequestCommands
            try:
                RentalRequestCommands.complete_period(ticket.source_rental_request)
            except Exception as exc:
                logger.warning(
                    "No se pudo completar el periodo de renta | ticket=%s err=%s",
                    ticket.uuid, exc,
                )

    @staticmethod
    def _release_assignments(ticket: OperationTicket) -> None:
        assignments = list(
            OperationAssignment.objects.select_related('assignee').filter(
                ticket=ticket,
                status=OperationAssignment.STATUS_ACTIVE,
                is_deleted=False,
            )
        )
        OperationAssignment.objects.filter(pk__in=[item.pk for item in assignments]).update(
            status=OperationAssignment.STATUS_RELEASED
        )
        for assignment in assignments:
            user = assignment.assignee
            if OperationAssignment.objects.filter(
                assignee=user,
                status=OperationAssignment.STATUS_ACTIVE,
                is_deleted=False,
            ).exists():
                continue
            if assignment.role == OperationAssignment.ROLE_TECHNICIAN:
                from accounts.models import TechnicianProfile
                TechnicianProfile.objects.filter(user=user, is_deleted=False).update(is_available=True)
            if assignment.role in (
                OperationAssignment.ROLE_DISPATCHER,
                OperationAssignment.ROLE_TRANSPORTER,
            ):
                DispatcherProfile.objects.filter(user=user, is_deleted=False).update(is_available=True)

    @staticmethod
    @transaction.atomic
    def upload_document(ticket: OperationTicket, doc_type: str, file, uploaded_by) -> OperationDocument:
        from accounts.services.commands import validate_file
        validate_file(
            file,
            max_size_mb=10,
            allowed_extensions=['.pdf', '.jpg', '.jpeg', '.png'],
            magic_bytes_check=True,
        )
        doc = OperationDocument.objects.create(
            ticket=ticket,
            doc_type=doc_type,
            file=file,
            uploaded_by=uploaded_by,
        )
        logger.info(
            "Documento subido | ticket=%s doc_type=%s doc=%s",
            ticket.uuid, doc_type, doc.uuid,
        )
        return doc

    @staticmethod
    @transaction.atomic
    def review_document(
        doc: OperationDocument,
        approved: bool,
        reviewed_by,
        reason: str = '',
    ) -> OperationDocument:
        doc.status      = OperationDocument.STATUS_APPROVED if approved else OperationDocument.STATUS_REJECTED
        doc.reviewed_by = reviewed_by
        doc.rejection_reason = '' if approved else reason
        doc.save(update_fields=['status', 'reviewed_by', 'rejection_reason', 'updated_at'])

        if approved:
            ticket = doc.ticket
            if ticket.status == OperationTicket.STATUS_DOCS_PENDING:
                all_required = _all_required_approved(ticket)
                if all_required:
                    TrackingEvent.objects.create(
                        ticket=ticket,
                        milestone=TrackingEvent.MILESTONE_DOCS_APPROVED,
                        description='Todos los documentos requeridos fueron aprobados.',
                        created_by=reviewed_by,
                    )
                    ticket.status = OperationTicket.STATUS_READY
                    ticket.save(update_fields=['status', 'updated_at'])

        return doc

    @staticmethod
    @transaction.atomic
    def submit_review(
        ticket: OperationTicket,
        reviewer,
        rating: int,
        comment: str = '',
        quality_rating: int = 5,
        punctuality_rating: int = 5,
        condition_rating: int = 5,
    ) -> OperationReview:
        if ticket.status != OperationTicket.STATUS_COMPLETED:
            raise ValueError("Solo se pueden calificar tickets completados.")
        if ticket.customer != reviewer:
            raise ValueError("Solo el cliente puede calificar su operacion.")
        if hasattr(ticket, 'review'):
            raise ValueError("Este ticket ya fue calificado.")

        review = OperationReview.objects.create(
            ticket=ticket,
            reviewer=reviewer,
            rating=rating,
            quality_rating=quality_rating,
            punctuality_rating=punctuality_rating,
            condition_rating=condition_rating,
            comment=comment,
        )

        _try_update_contractor_review(ticket, reviewer, rating, quality_rating, punctuality_rating)

        _user = ticket.customer
        _num  = ticket.ticket_number
        transaction.on_commit(
            lambda: _dispatch(
                user=_user,
                slug='operation_review_received',
                context={'ticket_number': _num, 'rating': rating},
                ws_group='sintel_notifications',
            )
        )

        return review

    @staticmethod
    def _generate_invoice_doc(ticket: OperationTicket, order) -> OperationDocument:
        doc = OperationDocument.objects.create(
            ticket=ticket,
            doc_type=OperationDocument.DOC_INVOICE,
            status=OperationDocument.STATUS_APPROVED,
        )
        logger.info(
            "Documento INVOICE creado (pendiente PDF) | ticket=%s order=%s",
            ticket.uuid, order.uuid,
        )
        return doc


class DispatcherCommands:

    @staticmethod
    @transaction.atomic
    def create(user, dispatcher_type, vehicle_plate='', vehicle_type='', coverage_cities=None) -> DispatcherProfile:
        # No se muta accounts.UserProfile.user_type acá -- DispatcherProfile es la fuente de
        # verdad de "este usuario es transportista/dispatcher". assign_resource(ROLE_CONTRACTOR)
        # consulta DispatcherProfile.dispatcher_type directamente para el caso FIELD_OPS.
        return DispatcherProfile.objects.create(
            user=user,
            dispatcher_type=dispatcher_type,
            vehicle_plate=vehicle_plate,
            vehicle_type=vehicle_type,
            coverage_cities=coverage_cities or [],
        )

    @staticmethod
    @transaction.atomic
    def update(profile: DispatcherProfile, **fields) -> DispatcherProfile:
        allowed = ('dispatcher_type', 'vehicle_plate', 'vehicle_type', 'coverage_cities',
                   'is_available', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(profile, key, val)
        profile.save()
        return profile

    @staticmethod
    @transaction.atomic
    def delete(profile: DispatcherProfile) -> None:
        profile.is_active  = False
        profile.is_deleted = True
        profile.save()


# ── helpers privados ──────────────────────────────────────────────────────────

def _dispatch(user, slug: str, context: dict, ws_group: str = None) -> None:
    from notifications.services.commands import NotificationCommands
    group = ws_group or f'user_{user.uuid}'
    NotificationCommands.dispatch_notification(
        user=user,
        template_slug=slug,
        context=context,
        ws_group=group,
    )


def _status_notification_slug(status: str):
    mapping = {
        OperationTicket.STATUS_ASSIGNED:    'operation_assigned',
        OperationTicket.STATUS_SCHEDULED:   'operation_scheduled',
        OperationTicket.STATUS_EN_ROUTE:    'operation_en_route',
        OperationTicket.STATUS_IN_PROGRESS: 'operation_in_progress',
        OperationTicket.STATUS_COMPLETED:   'operation_completed',
        OperationTicket.STATUS_CANCELLED:   'operation_cancelled',
    }
    return mapping.get(status)


def _all_required_approved(ticket: OperationTicket) -> bool:
    from operations.services.config import CUSTOMER_REQUIRED_DOCS
    required = CUSTOMER_REQUIRED_DOCS.get(ticket.operation_type, [])
    if not required:
        return True
    for doc_type in required:
        approved = ticket.documents.filter(
            doc_type=doc_type,
            status=OperationDocument.STATUS_APPROVED,
        ).exists()
        if not approved:
            return False
    return True


def _try_update_contractor_review(ticket, reviewer, rating, quality, punctuality) -> None:
    try:
        assignment = ticket.assignments.filter(
            role=OperationAssignment.ROLE_TECHNICIAN,
            status=OperationAssignment.STATUS_RELEASED,
        ).select_related('assignee__profile').first()

        if assignment is None:
            return

        from accounts.services import ProfileResolver
        contractor_profile = ProfileResolver.get_profile(assignment.assignee)
        if contractor_profile is None:
            return

        from accounts.models import ContractorReview
        ContractorReview.objects.update_or_create(
            contractor=contractor_profile,
            reviewer=reviewer,
            defaults={
                'quality_rating':        quality,
                'punctuality_rating':    punctuality,
                'professionalism_rating': rating,
                'communication_rating': rating,
                'compliance_rating':     rating,
            },
        )
    except Exception as exc:
        logger.warning(
            "No se pudo actualizar la calificacion del contratista | ticket=%s err=%s",
            ticket.uuid, exc,
        )
