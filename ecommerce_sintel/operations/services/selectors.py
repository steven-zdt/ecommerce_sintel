from django.shortcuts import get_object_or_404

from operations.models import (
    OperationTicket, TrackingEvent, OperationDocument,
    OperationAssignment, OperationReview, DispatcherProfile,
)


class OperationSelector:

    @staticmethod
    def get_ticket_for_user(uuid: str, user) -> OperationTicket:
        qs = OperationTicket.objects.select_related(
            'customer',
            'source_order',
            'source_rental_request',
        ).prefetch_related(
            'tracking_events',
            'documents',
            'assignments__assignee',
        )
        ticket = get_object_or_404(qs, uuid=uuid, is_deleted=False)
        if not (ticket.customer == user or (user.is_staff and user.is_superuser)):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied
        return ticket

    @staticmethod
    def list_for_user(user):
        return (
            OperationTicket.objects
            .filter(customer=user, is_deleted=False)
            .select_related('source_order', 'source_rental_request')
            .prefetch_related('tracking_events', 'documents')
            .order_by('-created_at')
        )

    @staticmethod
    def list_for_assignee(user):
        return (
            OperationTicket.objects
            .filter(assignments__assignee=user, is_deleted=False)
            .select_related('customer', 'source_order', 'source_rental_request')
            .prefetch_related('tracking_events', 'documents', 'assignments__assignee')
            .distinct()
            .order_by('-created_at')
        )

    @staticmethod
    def get_ticket_for_assignee(uuid: str, user) -> OperationTicket:
        return get_object_or_404(
            OperationSelector.list_for_assignee(user),
            uuid=uuid,
        )

    @staticmethod
    def get_timeline(ticket: OperationTicket):
        return (
            TrackingEvent.objects
            .filter(ticket=ticket, is_customer_visible=True)
            .order_by('created_at')
        )

    @staticmethod
    def list_for_board(filters: dict = None):
        qs = (
            OperationTicket.objects
            .filter(is_deleted=False)
            .select_related('customer', 'source_order', 'source_rental_request')
            .prefetch_related('assignments__assignee')
            .order_by('-created_at')
        )
        if not filters:
            return qs
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
        if filters.get('operation_type'):
            qs = qs.filter(operation_type=filters['operation_type'])
        if filters.get('assignee_id'):
            qs = qs.filter(assignments__assignee_id=filters['assignee_id'])
        if filters.get('scheduled_date'):
            qs = qs.filter(scheduled_date=filters['scheduled_date'])
        if filters.get('priority'):
            qs = qs.filter(priority=filters['priority'])
        return qs

    @staticmethod
    def get_document(ticket: OperationTicket, doc_uuid: str) -> OperationDocument:
        return get_object_or_404(
            OperationDocument,
            uuid=doc_uuid,
            ticket=ticket,
        )

    @staticmethod
    def metrics() -> dict:
        from django.db.models import Count
        qs = OperationTicket.objects.filter(is_deleted=False)
        totals = qs.aggregate(total=Count('id'))
        by_status = {
            row['status']: row['cnt']
            for row in qs.values('status').annotate(cnt=Count('id'))
        }
        return {'total': totals['total'], 'by_status': by_status}


class DispatcherSelector:

    @staticmethod
    def get_available(city: str = None, date=None):
        qs = DispatcherProfile.objects.filter(
            is_active=True,
            is_available=True,
            is_deleted=False,
        ).select_related('user')
        if city:
            qs = qs.filter(coverage_cities__contains=[city])
        return qs

    @staticmethod
    def list_board():
        return (
            DispatcherProfile.objects
            .filter(is_deleted=False)
            .select_related('user')
            .order_by('user__email')
        )
