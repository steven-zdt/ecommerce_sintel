import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from marketing.models import CampaignMedia, MarketingCampaign, FlashOffer, AgentRun
from marketing.services import MarketingSelector
from marketing.services.commands import CampaignMediaCommands, CampaignMediaValidationError, MarketingCommands
from marketing.channels.registry import AVAILABLE_CHANNELS, BROADCAST_CHANNELS
from marketing.api.serializers import (
    CampaignMediaSerializer,
    MarketingCampaignSerializer,
    FlashOfferSerializer,
    AgentRunSerializer,
    ConsolidatedDashboardSerializer
)

logger = logging.getLogger(__name__)


class MarketingCampaignViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = MarketingSelector.list_campaigns_for_admin()
    serializer_class = MarketingCampaignSerializer
    lookup_field = 'uuid'

    # Fase 33 (2026-09-24): eventos de observabilidad como log estructurado (no hay modelo de
    # auditoria reusable en marketing; CampaignLog ya audita el resultado por canal).
    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info("marketing_event=campaign_created campaign=%s user=%s",
                    instance.uuid, self.request.user.pk)

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info("marketing_event=campaign_updated campaign=%s user=%s channels=%s",
                    instance.uuid, self.request.user.pk, instance.channels)

    def perform_destroy(self, instance):
        uuid = instance.uuid
        instance.delete()
        logger.info("marketing_event=campaign_deleted campaign=%s user=%s", uuid, self.request.user.pk)

    # Fase 11-14 (2026-09-23): galeria de media -- acciones dedicadas, no un campo anidado
    # writable del serializer principal (ver docstring de CampaignMediaSerializer para el motivo).
    @extend_schema(summary="[Admin] Sube imagen o video a la campana")
    @action(detail=True, methods=['post'], url_path='media',
            parser_classes=[MultiPartParser, FormParser])
    def upload_media(self, request, uuid=None):
        campaign = self.get_object()
        file_obj = request.FILES.get('file')
        media_type = request.data.get('media_type', '').upper()
        if not file_obj:
            return Response({'detail': 'Se requiere el archivo file.'}, status=status.HTTP_400_BAD_REQUEST)
        if media_type not in (CampaignMedia.TYPE_IMAGE, CampaignMedia.TYPE_VIDEO):
            return Response({'detail': "media_type debe ser 'IMAGE' o 'VIDEO'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            media = CampaignMediaCommands.add_media(campaign, file_obj, media_type)
        except CampaignMediaValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CampaignMediaSerializer(media).data, status=status.HTTP_201_CREATED)

    # IMPORTANTE: el regex de media_uuid abajo (delete_media/toggle_media) esta restringido al
    # formato real de un UUID -- NUNCA "[^/.]+" generico. Motivo real (no cosmetico): DRF genera
    # las rutas de @action ordenando por `inspect.getmembers()`, es decir ALFABETICAMENTE por
    # nombre de metodo, NO por orden de declaracion en el archivo (confirmado empiricamente: mover
    # el metodo en el codigo no cambio nada). "delete_media" < "reorder_media" alfabeticamente, asi
    # que con un regex generico, la ruta de delete_media (que acepta cualquier string como
    # media_uuid) siempre intercepta primero a "/media/reorder/", matchea "reorder" como si fuera
    # el uuid, encuentra que el metodo POST no esta permitido ahi (es DELETE-only) y devuelve 405 --
    # sin backtracking a otros @action. Restringir el regex al shape real de un UUID es la unica
    # forma robusta de evitar esta colision (no depende de nombres ni de orden). Mismo bug de fondo
    # ya visto antes en esta sesion con /orders/orders/create-from-cart/ (ahi era otro mecanismo:
    # create_from_cart vs retrieve(), pero la misma familia de problema: rutas literales vs
    # parametrizadas del mismo router compitiendo por el mismo path).
    @extend_schema(summary="[Admin] Reordena la galeria de media de la campana")
    @action(detail=True, methods=['post'], url_path='media/reorder')
    def reorder_media(self, request, uuid=None):
        campaign = self.get_object()
        ordered_uuids = request.data.get('ordered_uuids', [])
        if not isinstance(ordered_uuids, list):
            return Response({'detail': 'ordered_uuids debe ser una lista.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            CampaignMediaCommands.reorder(campaign, ordered_uuids)
        except CampaignMediaValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        campaign.refresh_from_db()
        return Response(MarketingCampaignSerializer(campaign).data)

    _UUID_RE = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

    @extend_schema(summary="[Admin] Elimina media de la campana")
    @action(detail=True, methods=['delete'], url_path=fr'media/(?P<media_uuid>{_UUID_RE})')
    def delete_media(self, request, uuid=None, media_uuid=None):
        campaign = self.get_object()
        try:
            CampaignMediaCommands.delete_media(campaign, media_uuid)
        except CampaignMedia.DoesNotExist:
            return Response({'detail': 'Media no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Activa/desactiva media de la campana")
    @action(detail=True, methods=['post'], url_path=fr'media/(?P<media_uuid>{_UUID_RE})/toggle')
    def toggle_media(self, request, uuid=None, media_uuid=None):
        campaign = self.get_object()
        try:
            media = CampaignMediaCommands.toggle_active(campaign, media_uuid)
        except CampaignMedia.DoesNotExist:
            return Response({'detail': 'Media no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CampaignMediaSerializer(media).data)

    # Fase 17-18 (2026-09-23): "Enviar ahora" -- conecta el mecanismo de difusion que YA EXISTIA
    # (MarketingCommands.dispatch() -> CampaignLog -> send_via_channel_task, usado hasta ahora
    # solo por marketing/agent/brain.py) a un endpoint manual del CRUD admin. No se crea ningun
    # dispatcher nuevo, solo se expone el que ya funciona.
    #
    # Limitacion real HEREDADA de dispatch() (no introducida aqui, documentada en
    # MARKETING_GAPS.md): un solo `recipient` aplica a TODOS los canales seleccionados de la
    # campana en la misma llamada. Los canales de BROADCAST_CHANNELS (Facebook/Instagram/etc.)
    # ignoran `recipient` (publican a la pagina conectada, ver registry.py) y siempre son seguros
    # de despachar con el sentinel "broadcast". email/whatsapp SI necesitan un `recipient` real
    # (direccion/telefono) -- si la campana selecciona alguno de esos 2 SIN que el request
    # incluya `recipient`, se omiten (no se disparan a ciegas) y se reporta en la respuesta.
    @extend_schema(summary="[Admin] Dispara la difusion real de la campana por sus canales seleccionados")
    @action(detail=True, methods=['post'], url_path='send')
    def send_campaign(self, request, uuid=None):
        campaign = self.get_object()
        if not campaign.title:
            return Response({'detail': 'La campana necesita un titulo.'}, status=status.HTTP_400_BAD_REQUEST)
        channels = [c for c in (campaign.channels or []) if c in AVAILABLE_CHANNELS]
        if not channels:
            return Response({'detail': 'La campana no tiene ningun canal real seleccionado.'}, status=status.HTTP_400_BAD_REQUEST)

        recipient = (request.data.get('recipient') or '').strip()
        broadcast_channels = [c for c in channels if c in BROADCAST_CHANNELS]
        direct_channels = [c for c in channels if c not in BROADCAST_CHANNELS]
        skipped = []

        if broadcast_channels:
            MarketingCommands.dispatch(campaign, recipient='broadcast', channels=broadcast_channels)
        if direct_channels:
            if recipient:
                MarketingCommands.dispatch(campaign, recipient=recipient, channels=direct_channels)
            else:
                skipped = direct_channels

        campaign.refresh_from_db()
        logger.info("marketing_event=campaign_sent campaign=%s user=%s dispatched=%s skipped=%s",
                    campaign.uuid, request.user.pk, broadcast_channels + (direct_channels if recipient else []), skipped)
        payload = MarketingCampaignSerializer(campaign).data
        payload['dispatched_channels'] = broadcast_channels + (direct_channels if recipient else [])
        payload['skipped_channels'] = skipped
        return Response(payload)

    # Fase 22 (2026-09-23, PLAN_SINTEL_MARKETING_CAMPANAS_..._LOOP.md): reusa
    # MarketingCommands.build_message() -- el MISMO metodo que send_now() usa para el envio
    # real -- para que el preview jamas se desincronice de lo que realmente se envia.
    @extend_schema(summary="[Admin] Previsualiza el mensaje real que se enviaria por cada canal seleccionado")
    @action(detail=True, methods=['get'], url_path='preview')
    def preview(self, request, uuid=None):
        campaign = self.get_object()
        channels = [c for c in (campaign.channels or []) if c in AVAILABLE_CHANNELS]
        message = MarketingCommands.build_message(campaign, recipient='(destinatario real al enviar)')
        previews = [
            {
                'channel': channel,
                'subject': message.subject,
                'body': message.body,
                'media_url': message.media_url,
            }
            for channel in channels
        ]
        return Response({'channels': previews})

class FlashOfferViewSet(viewsets.ReadOnlyModelViewSet):
    """Ofertas flash activas. Lectura publica (vitrina de la tienda)."""
    permission_classes = [permissions.AllowAny]
    serializer_class = FlashOfferSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        # M-02 (auditoria enterprise): list_flash_offers() solo filtraba
        # is_active=True, sin ventana de tiempo -- una oferta ya vencida o
        # que aun no empieza (is_active=True pero start_time futuro) se
        # mostraba en la vitrina publica. list_active_flash_offers() ya
        # existia, optimizado (select_related/prefetch_related) y con el
        # filtro de ventana correcto, pero no se usaba en ningun lado.
        return MarketingSelector.list_active_flash_offers()

class AgentRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = MarketingSelector.list_agent_runs()
    serializer_class = AgentRunSerializer
    lookup_field = 'uuid'

class DashboardViewSet(viewsets.ViewSet):
    """
    Consolidated Intelligence Dashboard for Marketing.
    """
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: ConsolidatedDashboardSerializer})
    def list(self, request):
        data = MarketingSelector.get_consolidated_dashboard()
        serializer = ConsolidatedDashboardSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
