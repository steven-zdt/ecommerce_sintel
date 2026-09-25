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
    AIConfigRevisionSerializer,
    AIModelInputSerializer,
    AIModelSerializer,
    AIModelSettingsInputSerializer,
    MCPServerInputSerializer,
    MCPServerSerializer,
    AIProviderInputSerializer,
    AIProviderSerializer,
)
from dashboard.api.views import ADMIN_PERMISSIONS
from ai_provider.services.activation import ActivationCheckFailed
from ai_provider.services.revisions import RollbackError
from dashboard.services.admin_orchestrators import AIProviderAdminOrchestrator


def _parse_version(request):
    try:
        return int(request.data.get('version'))
    except (TypeError, ValueError):
        raise DRFValidationError({'version': 'Numero de version invalido.'})


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

    @action(detail=True, methods=['post'], url_path='health')
    def health(self, request, uuid=None):
        """Comprueba el proveedor (ping/catalogo, nunca una generacion) y persiste HEALTHY/DEGRADED/UNAVAILABLE/MISCONFIGURED/DISABLED."""
        provider = self._get_or_404(uuid)
        return Response(AIProviderAdminOrchestrator.check_health(provider.uuid, user=request.user))

    @action(detail=True, methods=['post'], url_path='primary')
    def primary(self, request, uuid=None):
        """Usa un modelo de ESTE proveedor como primario del canal (con validacion previa; `force=true` la omite). 409 si la validacion falla."""
        provider = self._get_or_404(uuid)
        model_uuid = request.data.get('model_uuid')
        if not model_uuid:
            default = provider.models.filter(is_deleted=False, is_active=True).order_by('-is_default', 'model_id').first()
            model_uuid = default and str(default.uuid)
        if not model_uuid or not provider.models.filter(uuid=model_uuid, is_deleted=False).exists():
            raise DRFValidationError({'model_uuid': 'Indica un modelo activo de este proveedor.'})
        force = str(request.data.get('force', '')).lower() in ('true', '1')
        try:
            config = AIProviderAdminOrchestrator.set_primary_model(model_uuid, request.user, channel=request.data.get('channel', 'support_chat'), force=force)
        except ActivationCheckFailed as exc:
            return Response({'error': 'validation_failed', 'report': exc.report}, status=status.HTTP_409_CONFLICT)
        return Response(AIChannelConfigSerializer(config).data)

    @action(detail=True, methods=['post'], url_path='fallback')
    def fallback(self, request, uuid=None):
        """Agrega un modelo de este proveedor a la cadena de fallback ({model_uuid, position?}). Determinista: nunca el primario ni repetidos."""
        provider = self._get_or_404(uuid)
        model_uuid = request.data.get('model_uuid')
        if not model_uuid:
            raise DRFValidationError({'model_uuid': 'Requerido.'})
        try:
            config = AIProviderAdminOrchestrator.add_fallback_model(
                model_uuid, request.user, position=request.data.get('position'),
                channel=request.data.get('channel', 'support_chat'), provider_uuid=provider.uuid)
        except AIModel.DoesNotExist:
            raise Http404
        except (ValueError, DjangoValidationError) as exc:
            raise DRFValidationError({'model_uuid': str(exc)})
        return Response(AIChannelConfigSerializer(config).data)

    @action(detail=True, methods=['patch'], url_path='model-settings/(?P<model_uuid>[^/.]+)')
    def model_settings(self, request, uuid=None, model_uuid=None):
        """Parametros de generacion (temperature/top_p/max_tokens/context_window) y capacidades manuales de un modelo."""
        provider = self._get_or_404(uuid)
        if not provider.models.filter(uuid=model_uuid, is_deleted=False).exists():
            raise Http404
        serializer = AIModelSettingsInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            model = AIProviderAdminOrchestrator.update_model_settings(model_uuid, serializer.validated_data, user=request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(AIModelSerializer(model).data)

    @action(detail=True, methods=['post'], url_path='detect-capabilities/(?P<model_uuid>[^/.]+)')
    def detect_capabilities(self, request, uuid=None, model_uuid=None):
        """"Detectar capacidades": pregunta al proveedor; lo que no declara queda desconocido (null), nunca se inventa."""
        provider = self._get_or_404(uuid)
        if not provider.models.filter(uuid=model_uuid, is_deleted=False).exists():
            raise Http404
        return Response(AIModelSerializer(AIProviderAdminOrchestrator.detect_model_capabilities(model_uuid, user=request.user)).data)

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        return Response(AIConfigRevisionSerializer(AIProviderAdminOrchestrator.provider_history(provider.uuid), many=True).data)

    @action(detail=True, methods=['post'], url_path='rollback')
    def rollback(self, request, uuid=None):
        provider = self._get_or_404(uuid)
        try:
            provider = AIProviderAdminOrchestrator.rollback_provider(provider.uuid, _parse_version(request), request.user)
        except RollbackError as exc:
            raise DRFValidationError({'version': str(exc)})
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
        force = str(request.data.get('force', '')).lower() in ('true', '1')
        try:
            config = AIProviderAdminOrchestrator.set_primary_model(model_uuid, request.user, channel=channel, force=force)
        except AIModel.DoesNotExist:
            raise Http404
        except ActivationCheckFailed as exc:
            # 409: la configuracion actual NO cambio. El reporte no contiene secretos.
            return Response({'error': 'validation_failed', 'report': exc.report}, status=status.HTTP_409_CONFLICT)
        return Response(AIChannelConfigSerializer(config).data)

    @action(detail=False, methods=['post'], url_path='validate-model')
    def validate_model(self, request):
        """Prueba previa sin persistir: {model_uuid} -> {ok, checks, warnings, latency_ms} o 409 con el motivo."""
        try:
            report = AIProviderAdminOrchestrator.validate_model(request.data.get('model_uuid'), channel=request.data.get('channel', 'support_chat'))
        except (AIModel.DoesNotExist, DRFValidationError, DjangoValidationError, ValueError) as exc:
            if isinstance(exc, ActivationCheckFailed):
                return Response({'error': 'validation_failed', 'report': exc.report}, status=status.HTTP_409_CONFLICT)
            raise Http404
        return Response(report)

    @action(detail=False, methods=['post'], url_path='set-fallback-chain')
    def set_fallback_chain(self, request):
        channel = request.data.get('channel', 'support_chat')
        model_uuids = request.data.get('model_uuids', [])
        try:
            config = AIProviderAdminOrchestrator.set_fallback_chain(model_uuids, request.user, channel=channel)
        except AIModel.DoesNotExist:
            raise Http404
        return Response(AIChannelConfigSerializer(config).data)

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        channel = request.query_params.get('channel', 'support_chat')
        return Response(AIConfigRevisionSerializer(AIProviderAdminOrchestrator.channel_history(channel), many=True).data)

    @action(detail=False, methods=['post'], url_path='rollback')
    def rollback(self, request):
        channel = request.data.get('channel', 'support_chat')
        try:
            config = AIProviderAdminOrchestrator.rollback_channel(_parse_version(request), request.user, channel=channel)
        except RollbackError as exc:
            raise DRFValidationError({'version': str(exc)})
        return Response(AIChannelConfigSerializer(config).data)


class AdminMCPServerViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/ai-mcp-servers/ -- PLAN_LLMDINAMICO sec. 5: servidores MCP como integracion INDEPENDIENTE de los proveedores LLM
    (server_url, transporte, autenticacion, capacidades, estado). Solo IsAdminUser; la API key nunca se devuelve.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def _get_or_404(self, uuid):
        from ai_provider.models import MCPServer
        try:
            return MCPServer.objects.get(uuid=uuid, is_deleted=False)
        except (MCPServer.DoesNotExist, DjangoValidationError, ValueError):
            raise Http404

    def list(self, request):
        return Response(MCPServerSerializer(AIProviderAdminOrchestrator.list_mcp_servers(), many=True).data)

    def retrieve(self, request, uuid=None):
        return Response(MCPServerSerializer(self._get_or_404(uuid)).data)

    def create(self, request):
        serializer = MCPServerInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            server = AIProviderAdminOrchestrator.create_mcp_server(serializer.validated_data, user=request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(MCPServerSerializer(server).data, status=status.HTTP_201_CREATED)

    def update(self, request, uuid=None):
        self._get_or_404(uuid)
        serializer = MCPServerInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            server = AIProviderAdminOrchestrator.update_mcp_server(uuid, serializer.validated_data, user=request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(MCPServerSerializer(server).data)

    partial_update = update

    def destroy(self, request, uuid=None):
        self._get_or_404(uuid)
        AIProviderAdminOrchestrator.delete_mcp_server(uuid, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='test')
    def test(self, request, uuid=None):
        """Handshake MCP real (initialize + tools/list). Devuelve el reporte (sin secretos) y persiste estado/capacidades."""
        self._get_or_404(uuid)
        return Response(AIProviderAdminOrchestrator.test_mcp_server(uuid, user=request.user))
