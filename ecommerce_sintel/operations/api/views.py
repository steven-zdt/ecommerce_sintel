from django.contrib.auth import get_user_model
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from users.api.permissions import IsAuthenticatedActiveUser, IsAdminUser, IsOperationalUser
from operations.models import OperationTicket, OperationDocument
from operations.services.commands import OperationCommands, DispatcherCommands
from operations.services.selectors import OperationSelector, DispatcherSelector
from operations.api.serializers import (
    OperationTicketListSerializer,
    OperationTicketDetailSerializer,
    DocumentUploadSerializer,
    ReviewSubmitSerializer,
    DispatcherProfileSerializer,
    AdminTicketBoardSerializer,
    AdminAssignSerializer,
    AdminScheduleSerializer,
    AdminTransitionSerializer,
    AdminDocReviewSerializer,
    TrackingEventSerializer,
    OperationDocumentSerializer,
)

User = get_user_model()


class CustomerOperationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoints de solo lectura para el cliente: /api/v1/operations/my/
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get_queryset(self):
        return OperationSelector.list_for_user(self.request.user)

    def get_object(self):
        return OperationSelector.get_ticket_for_user(
            uuid=self.kwargs['pk'],
            user=self.request.user,
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OperationTicketDetailSerializer
        return OperationTicketListSerializer

    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, pk=None):
        ticket = self.get_object()
        events = OperationSelector.get_timeline(ticket)
        return Response(TrackingEventSerializer(events, many=True).data)

    @action(detail=True, methods=['post'], url_path='upload-document')
    def upload_document(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status not in (
            OperationTicket.STATUS_CREATED,
            OperationTicket.STATUS_DOCS_PENDING,
        ):
            return Response(
                {'detail': 'No se pueden subir documentos en el estado actual.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = DocumentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        doc = OperationCommands.upload_document(
            ticket=ticket,
            doc_type=ser.validated_data['doc_type'],
            file=ser.validated_data['file'],
            uploaded_by=request.user,
        )
        return Response(OperationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='review')
    def submit_review(self, request, pk=None):
        ticket = self.get_object()
        ser = ReviewSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        review = OperationCommands.submit_review(
            ticket=ticket,
            reviewer=request.user,
            **ser.validated_data,
        )
        from operations.api.serializers import OperationReviewSerializer
        return Response(OperationReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class OperationalTaskViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Tareas propias del personal operativo autenticado."""
    permission_classes = [IsOperationalUser]
    serializer_class = OperationTicketDetailSerializer

    def get_queryset(self):
        return OperationSelector.list_for_assignee(self.request.user)

    def get_object(self):
        return OperationSelector.get_ticket_for_assignee(
            uuid=self.kwargs['pk'],
            user=self.request.user,
        )

    @action(detail=True, methods=['post'], url_path='transition')
    def transition_status(self, request, pk=None):
        ticket = self.get_object()
        if not ticket.assignments.filter(
            assignee=request.user,
            status='ACTIVE',
            is_deleted=False,
        ).exists():
            return Response(
                {'detail': 'La asignacion ya no esta activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AdminTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        allowed_for_staff = {
            OperationTicket.STATUS_EN_ROUTE,
            OperationTicket.STATUS_IN_PROGRESS,
            OperationTicket.STATUS_COMPLETED,
        }
        if new_status not in allowed_for_staff:
            return Response(
                {'detail': 'El personal operativo no puede aplicar ese estado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            OperationCommands.transition_status(
                ticket=ticket,
                new_status=new_status,
                by=request.user,
                note=serializer.validated_data.get('note', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OperationTicketDetailSerializer(ticket).data)


class AdminOperationViewSet(viewsets.GenericViewSet):
    """
    Panel de administracion: /api/v1/dashboard/operations/
    """
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        return AdminTicketBoardSerializer

    def list(self, request):
        filters = {
            k: v for k, v in request.query_params.items()
            if k in ('status', 'operation_type', 'assignee_id', 'scheduled_date', 'priority')
        }
        qs = OperationSelector.list_for_board(filters or None)
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = AdminTicketBoardSerializer(page, many=True)
            return self.get_paginated_response(ser.data)
        return Response(AdminTicketBoardSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        ticket = OperationSelector.get_ticket_for_user(uuid=pk, user=request.user)
        return Response(OperationTicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        ticket = _get_ticket(pk)
        ser = AdminAssignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            assignee = User.objects.get(pk=ser.validated_data['assignee_id'], is_active=True)
            OperationCommands.assign_resource(
                ticket=ticket,
                assignee=assignee,
                role=ser.validated_data['role'],
                assigned_by=request.user,
            )
        except User.DoesNotExist:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Recurso asignado.'})

    @action(detail=True, methods=['get'], url_path='available-staff')
    def available_staff(self, request, pk=None):
        ticket = _get_ticket(pk)
        staff = []
        if ticket.operation_type == OperationTicket.SERVICE:
            from accounts.models import TechnicianProfile, UserProfile
            from accounts.services.profile_registry import CONTRACTOR_ASSIGNABLE_TYPES
            from operations.models import DispatcherProfile
            technicians = TechnicianProfile.objects.filter(
                is_available=True,
                is_deleted=False,
                user__is_active=True,
            ).select_related('user__profile')
            staff.extend(_staff_item(item.user, 'TECHNICIAN') for item in technicians)

            contractor_user_ids = set()
            contractors = UserProfile.objects.filter(
                user_type__in=CONTRACTOR_ASSIGNABLE_TYPES,
                user__is_active=True,
                is_deleted=False,
            ).select_related('user')
            for item in contractors:
                contractor_user_ids.add(item.user_id)
                staff.append(_staff_item(item.user, 'CONTRACTOR'))

            # Los dispatchers FIELD_OPS tambien son elegibles como ROLE_CONTRACTOR
            # (ver operations.services.commands.assign_resource) sin depender de que su
            # UserProfile.user_type haya sido mutado -- DispatcherProfile es su propia fuente
            # de verdad.
            field_ops = DispatcherProfile.objects.filter(
                dispatcher_type=DispatcherProfile.FIELD_OPS,
                is_active=True,
                is_deleted=False,
                user__is_active=True,
            ).select_related('user')
            for item in field_ops:
                if item.user_id not in contractor_user_ids:
                    staff.append(_staff_item(item.user, 'CONTRACTOR'))
        else:
            dispatchers = DispatcherSelector.get_available(city=ticket.location_city)
            staff.extend(_staff_item(item.user, 'TRANSPORTER') for item in dispatchers)
        return Response(staff)

    @action(detail=True, methods=['post'], url_path='auto-assign')
    def auto_assign(self, request, pk=None):
        ticket = _get_ticket(pk)
        try:
            OperationCommands.auto_assign(ticket=ticket, assigned_by=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Auto-asignacion completada.'})

    @action(detail=True, methods=['post'], url_path='schedule')
    def schedule(self, request, pk=None):
        ticket = _get_ticket(pk)
        ser = AdminScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            OperationCommands.schedule(
                ticket=ticket,
                date=ser.validated_data['scheduled_date'],
                start_time=ser.validated_data['scheduled_time_start'],
                end_time=ser.validated_data['scheduled_time_end'],
                by=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Visita programada.'})

    @action(detail=True, methods=['post'], url_path='transition')
    def transition_status(self, request, pk=None):
        ticket = _get_ticket(pk)
        ser = AdminTransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            OperationCommands.transition_status(
                ticket=ticket,
                new_status=ser.validated_data['status'],
                by=request.user,
                note=ser.validated_data.get('note', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Estado actualizado.'})

    @action(detail=True, methods=['post'], url_path='documents/(?P<doc_uuid>[^/.]+)/review')
    def review_document(self, request, pk=None, doc_uuid=None):
        ticket = _get_ticket(pk)
        doc = OperationSelector.get_document(ticket, doc_uuid)
        ser = AdminDocReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        OperationCommands.review_document(
            doc=doc,
            approved=ser.validated_data['approved'],
            reviewed_by=request.user,
            reason=ser.validated_data.get('reason', ''),
        )
        return Response({'detail': 'Documento revisado.'})

    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics(self, request):
        return Response(OperationSelector.metrics())


class AdminDispatcherViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD de despachadores: /api/v1/dashboard/dispatchers/
    """
    permission_classes = [IsAdminUser]
    serializer_class   = DispatcherProfileSerializer

    def get_queryset(self):
        return DispatcherSelector.list_board()

    def create(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'user_id': 'Requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        user    = User.objects.get(pk=user_id)
        profile = DispatcherCommands.create(
            user=user,
            dispatcher_type=request.data.get('dispatcher_type', 'DRIVER'),
            vehicle_plate=request.data.get('vehicle_plate', ''),
            vehicle_type=request.data.get('vehicle_type', ''),
            coverage_cities=request.data.get('coverage_cities', []),
        )
        return Response(DispatcherProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        from operations.models import DispatcherProfile
        profile = DispatcherProfile.objects.get(uuid=pk)
        allowed = ('dispatcher_type', 'vehicle_plate', 'vehicle_type',
                   'coverage_cities', 'is_available', 'is_active')
        fields = {k: v for k, v in request.data.items() if k in allowed}
        profile = DispatcherCommands.update(profile, **fields)
        return Response(DispatcherProfileSerializer(profile).data)

    def destroy(self, request, pk=None):
        from operations.models import DispatcherProfile
        profile = DispatcherProfile.objects.get(uuid=pk)
        DispatcherCommands.delete(profile)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_ticket(pk: str) -> OperationTicket:
    from django.shortcuts import get_object_or_404
    return get_object_or_404(OperationTicket, uuid=pk, is_deleted=False)


def _staff_item(user, role: str) -> dict:
    return {
        'id': user.pk,
        'uuid': str(user.uuid),
        'email': user.email,
        'name': user.get_full_name(),
        'role': role,
    }
