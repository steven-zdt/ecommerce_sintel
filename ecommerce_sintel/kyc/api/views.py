from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from users.api.permissions import IsAuthenticatedActiveUser, IsAdminUser
from kyc.models import UserVerification, VerificationDocument
from kyc.services.commands import KycCommands
from kyc.services.selectors import KycSelector
from kyc.api.serializers import (
    UserVerificationSerializer,
    AdminVerificationListSerializer,
    AdminVerificationDetailSerializer,
    VerificationDocumentSerializer,
    DocumentUploadSerializer,
    RequestUpgradeSerializer,
    AdminForceApproveSerializer,
    AdminRejectSerializer,
    AdminRequestInfoSerializer,
    AdminBlockSerializer,
    AdminDocReviewSerializer,
)


def _get_own_verification(user) -> UserVerification:
    verification = KycSelector.get_own_verification(user)
    if verification is None:
        raise NotFound("No existe un proceso de verificacion para este usuario.")
    return verification


class KycViewSet(viewsets.ViewSet):
    """Auto-servicio KYC del usuario autenticado (aunque su estado sea PENDING)."""
    permission_classes = [IsAuthenticatedActiveUser]

    ACTION_THROTTLE_SCOPES = {
        'upload_document': 'kyc_upload',
        'request_upgrade': 'kyc_upgrade',
    }

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    @action(detail=False, methods=['get'], url_path='verification')
    def verification(self, request):
        verification = _get_own_verification(request.user)
        return Response(UserVerificationSerializer(verification).data)

    @action(detail=False, methods=['post'], url_path='submit-for-review')
    def submit_for_review(self, request):
        verification = _get_own_verification(request.user)
        verification = KycCommands.submit_for_review(verification, by=request.user)
        return Response(UserVerificationSerializer(verification).data)

    @action(detail=False, methods=['post'], url_path='upload-document')
    def upload_document(self, request):
        verification = _get_own_verification(request.user)
        ser = DocumentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        doc = KycCommands.upload_document(
            verification=verification,
            doc_type=ser.validated_data['doc_type'],
            file=ser.validated_data['file'],
            uploaded_by=request.user,
        )
        return Response(VerificationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='request-upgrade')
    def request_upgrade(self, request):
        """
        Un CUSTOMER ya APPROVED pide convertirse en profesional. Reabre su
        propia UserVerification (PENDING) para que suba los mismos 5
        documentos requeridos y la envie a revision -- ver
        KycCommands.request_upgrade.
        """
        verification = _get_own_verification(request.user)
        ser = RequestUpgradeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verification = KycCommands.request_upgrade(
            verification, requested_user_type=ser.validated_data['requested_user_type'], by=request.user,
        )
        return Response(UserVerificationSerializer(verification).data)


class VerificationDocumentViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Documentos propios del usuario autenticado: listar, eliminar y descargar."""
    permission_classes = [IsAuthenticatedActiveUser]
    serializer_class = VerificationDocumentSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        verification = KycSelector.get_own_verification(self.request.user)
        if verification is None:
            return VerificationDocument.objects.none()
        return KycSelector.list_own_documents(verification)

    def perform_destroy(self, instance):
        KycCommands.delete_document(instance, requesting_user=self.request.user)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, uuid=None):
        doc = get_object_or_404(
            VerificationDocument.objects.select_related('verification__user'),
            uuid=uuid, is_deleted=False,
        )
        is_owner = doc.verification.user_id == request.user.pk
        is_admin = bool(request.user.is_staff and request.user.is_superuser)
        if not (is_owner or is_admin):
            raise PermissionDenied("No tienes permiso para descargar este documento.")
        if not is_owner:
            KycCommands.mark_document_opened(doc, request.user)
        return FileResponse(
            doc.file.open('rb'), as_attachment=True,
            filename=doc.original_filename or doc.file.name,
        )


class AdminKycViewSet(viewsets.GenericViewSet):
    """Panel administrador: /api/v1/auth/admin/verifications/"""
    permission_classes = [IsAdminUser]
    lookup_field = 'uuid'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdminVerificationDetailSerializer
        return AdminVerificationListSerializer

    def list(self, request):
        filters = {
            k: v for k, v in request.query_params.items()
            if k in ('status', 'search', 'requested_user_type')
        }
        qs = KycSelector.list_queue(filters)
        page = self.paginate_queryset(qs)
        serializer = AdminVerificationListSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, uuid=None):
        verification = KycSelector.get_verification_for_admin(uuid)
        return Response(AdminVerificationDetailSerializer(verification).data)

    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics(self, request):
        return Response(KycSelector.get_admin_metrics())

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, uuid=None):
        verification = KycSelector.get_verification_for_admin(uuid)
        verification = KycCommands.approve(verification, reviewed_by=request.user)
        return Response(AdminVerificationDetailSerializer(verification).data)

    @action(detail=True, methods=['post'], url_path='force-approve')
    def force_approve(self, request, uuid=None):
        """
        Aprobacion manual: activa el acceso del usuario de inmediato sin
        exigir que cada documento este individualmente aprobado. Pensada
        para el panel /panel/usuarios (ver KycCommands.force_approve).
        """
        verification = KycSelector.get_verification_for_admin(uuid)
        ser = AdminForceApproveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verification = KycCommands.force_approve(
            verification, reviewed_by=request.user, note=ser.validated_data.get('note', ''),
        )
        return Response(AdminVerificationDetailSerializer(verification).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, uuid=None):
        verification = KycSelector.get_verification_for_admin(uuid)
        ser = AdminRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verification = KycCommands.reject(verification, reviewed_by=request.user, reason=ser.validated_data['reason'])
        return Response(AdminVerificationDetailSerializer(verification).data)

    @action(detail=True, methods=['post'], url_path='request-info')
    def request_info(self, request, uuid=None):
        verification = KycSelector.get_verification_for_admin(uuid)
        ser = AdminRequestInfoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verification = KycCommands.request_more_info(
            verification, reviewed_by=request.user, message=ser.validated_data['message'],
        )
        return Response(AdminVerificationDetailSerializer(verification).data)

    @action(detail=True, methods=['post'], url_path='block')
    def block(self, request, uuid=None):
        verification = KycSelector.get_verification_for_admin(uuid)
        ser = AdminBlockSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verification = KycCommands.block(verification, reviewed_by=request.user, reason=ser.validated_data['reason'])
        return Response(AdminVerificationDetailSerializer(verification).data)

    @action(detail=True, methods=['post'], url_path='documents/(?P<doc_uuid>[^/.]+)/review')
    def review_document(self, request, uuid=None, doc_uuid=None):
        verification = KycSelector.get_verification_for_admin(uuid)
        doc = get_object_or_404(verification.documents, uuid=doc_uuid, is_deleted=False)
        ser = AdminDocReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        KycCommands.review_document(
            document=doc,
            approved=ser.validated_data['approved'],
            reviewed_by=request.user,
            reason=ser.validated_data.get('reason', ''),
        )
        return Response({'detail': 'Documento revisado.'})
