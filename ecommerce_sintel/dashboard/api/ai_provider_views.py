"""
dashboard/api/ai_provider_views.py

ViewSets del panel admin de proveedores/modelos de IA -- `/api/v1/dashboard/
ai-providers/` (plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES", FASE 3,
2026-08-13). Archivo separado del `views.py` principal (mismo criterio de split que
`services_catalog_views.py`). Zero ORM directo -- todo delega en
`AIProviderAdminOrchestrator` (dashboard/services/admin_orchestrators.py), que a su
vez delega en `ai_provider.services.selectors/commands`.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from ai_provider.models import AIModel, AIProvider
from dashboard.api.ai_provider_serializers import (
    AIChannelConfigSerializer,
    AIModelInputSerializer,
    AIModelSerializer,
    AIProviderInputSerializer,
    AIProviderSerializer,
)
from dashboard.api.views import ADMIN_PERMISSIONS
from dashboard.services.admin_orchestrators import AIProviderAdminOrchestrator


class AdminAIProviderViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/ai-providers/
    CRUD de proveedores + submodelos + acciones de test-connection/discover-models/
    add-model. `lookup_field='uuid'` -- consistente con el resto del proyecto (nunca
    exponer el `id` autoincremental en URLs).
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def _get_or_404(self, uuid):
        try:
            return AIProviderAdminOrchestrator.get_provider(uuid)
        except AIProvider.DoesNotExist:
            raise Http404

    def list(self, request):
        providers = AIProviderAdminOrchestrator.list_providers()
        return Response(AIProviderSerializer(providers, many=True).data)

    def retrieve(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        return Response(AIProviderSerializer(provider).data)

    def create(self, request):
        serializer = AIProviderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            provider = AIProviderAdminOrchestrator.create_provider(serializer.validated_data, user=request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(AIProviderSerializer(provider).data, status=status.HTTP_201_CREATED)

    def update(self, request, uuid=None):
        serializer = AIProviderInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            provider = AIProviderAdminOrchestrator.update_provider(uuid, serializer.validated_data, user=request.user)
        except AIProvider.DoesNotExist:
            raise Http404
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(AIProviderSerializer(provider).data)

    partial_update = update

    def destroy(self, request, uuid=None):
        try:
            AIProviderAdminOrchestrator.delete_provider(uuid, user=request.user)
        except AIProvider.DoesNotExist:
            raise Http404
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        provider = AIProviderAdminOrchestrator.test_connection(provider.uuid, user=request.user)
        return Response(AIProviderSerializer(provider).data)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        provider = AIProviderAdminOrchestrator.activate_provider(provider.uuid, user=request.user)
        return Response(AIProviderSerializer(provider).data)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        provider = AIProviderAdminOrchestrator.deactivate_provider(provider.uuid, user=request.user)
        return Response(AIProviderSerializer(provider).data)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        provider = AIProviderAdminOrchestrator.set_default_provider(provider.uuid, user=request.user)
        return Response(AIProviderSerializer(provider).data)

    @action(detail=True, methods=['get'], url_path='discover-models')
    def discover_models(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        discovered = AIProviderAdminOrchestrator.discover_models(provider.uuid)
        return Response({'discovered': discovered})

    @action(detail=True, methods=['post'], url_path='models')
    def add_model(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        serializer = AIModelInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        model = AIProviderAdminOrchestrator.add_model(
            provider.uuid, serializer.validated_data['model_id'],
            display_name=serializer.validated_data.get('display_name', ''), user=request.user,
        )
        return Response(AIModelSerializer(model).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='models/(?P<model_uuid>[^/.]+)')
    def delete_model(self, request, uuid=None, model_uuid=None):
        try:
            AIProviderAdminOrchestrator.delete_model(model_uuid, user=request.user)
        except AIModel.DoesNotExist:
            raise Http404
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAIChannelConfigViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/ai-channel-config/
    Modelo primario + cadena de fallback del canal `support_chat` (unico canal hoy).
    """
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        channel = request.query_params.get('channel', 'support_chat')
        config = AIProviderAdminOrchestrator.get_channel_config(channel)
        return Response(AIChannelConfigSerializer(config).data)

    @action(detail=False, methods=['post'], url_path='set-primary')
    def set_primary(self, request):
        channel = request.data.get('channel', 'support_chat')
        model_uuid = request.data.get('model_uuid') or None
        try:
            config = AIProviderAdminOrchestrator.set_primary_model(model_uuid, request.user, channel=channel)
        except AIModel.DoesNotExist:
            raise Http404
        return Response(AIChannelConfigSerializer(config).data)

    @action(detail=False, methods=['post'], url_path='set-fallback-chain')
    def set_fallback_chain(self, request):
        channel = request.data.get('channel', 'support_chat')
        model_uuids = request.data.get('model_uuids', [])
        try:
            config = AIProviderAdminOrchestrator.set_fallback_chain(model_uuids, request.user, channel=channel)
        except AIModel.DoesNotExist:
            raise Http404
        return Response(AIChannelConfigSerializer(config).data)
