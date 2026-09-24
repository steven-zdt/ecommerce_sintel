"""
Marketing Campaign Commands
Orchestrates campaign dispatch across selected channels.
Uses Celery for async execution to keep the API response fast.
"""
import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from marketing.models import CampaignMedia, MarketingCampaign, CampaignLog
from marketing.channels.registry import get_adapter
from marketing.channels.base import CampaignMessage

logger = logging.getLogger(__name__)

# Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): el canal whatsapp de marketing usa
# el MISMO phone_number_id/token de Meta que notifications (envio transaccional de soporte,
# OTPs) -- ver organization.services.selectors.OrganizationSelector.get_integration_settings()
# vs notifications/clients/whatsapp.py. Sin limite propio, una rafaga de campanas de marketing
# podia consumir la cuota de mensajeria de esa cuenta y degradar/bloquear mensajes
# transaccionales de soporte que comparten el mismo numero. Mismo patron atomico
# cache.add()/cache.incr() ya usado en notifications/services/commands.py::_channel_rate_limited
# y en support/services/commands.py::is_message_flood_limited.
_WHATSAPP_MARKETING_RATE_LIMIT_KEY = 'marketing_whatsapp_throttle'
_WHATSAPP_MARKETING_RATE_LIMIT_MAX = 20
_WHATSAPP_MARKETING_RATE_LIMIT_WINDOW_SECONDS = 3600


def _marketing_whatsapp_rate_limited() -> bool:
    cache.add(_WHATSAPP_MARKETING_RATE_LIMIT_KEY, 0, timeout=_WHATSAPP_MARKETING_RATE_LIMIT_WINDOW_SECONDS)
    count = cache.incr(_WHATSAPP_MARKETING_RATE_LIMIT_KEY)
    return count > _WHATSAPP_MARKETING_RATE_LIMIT_MAX


class MarketingCommands:

    @staticmethod
    def build_message(campaign: MarketingCampaign, recipient: str) -> CampaignMessage:
        """
        Construye el `CampaignMessage` real de una campana -- UNICO lugar que arma el
        cuerpo final, usado tanto por `send_now()` (envio real) como por el endpoint de
        preview (Fase 22, PLAN_SINTEL_MARKETING_CAMPANAS_..._LOOP.md, 2026-09-23).

        Hallazgo real corregido en esta fase: `send_now()` solo armaba
        `CampaignMessage(subject=campaign.title, body=campaign.content)` -- ignoraba items/
        beneficios/CTA/terminos agregados en Fase 3-10. El mensaje real que salia por
        cualquier canal nunca reflejaba lo que el admin configuraba en el formulario mas
        alla del titulo/contenido base.
        """
        from django.contrib.contenttypes.models import ContentType

        lines = [campaign.content] if campaign.content else []

        for item in campaign.items.all():
            try:
                obj = item.content_type.model_class().objects.get(uuid=item.object_uuid)
                name = getattr(obj, 'name', None) or str(obj)
            except Exception:
                name = f"{item.content_type.model}:{item.object_uuid}"
            qty = f" x{item.quantity}" if item.quantity > 1 else ""
            lines.append(f"- {name}{qty}")

        benefits = list(campaign.benefits.all())
        if benefits:
            lines.append("Beneficios:")
            for b in benefits:
                lines.append(f"- {b.label}")

        if campaign.cta_label:
            cta = campaign.cta_label
            if campaign.cta_url:
                cta += f": {campaign.cta_url}"
            lines.append(cta)

        if campaign.terms:
            lines.append(f"Condiciones: {campaign.terms}")

        media_url = None
        first_media = campaign.media.filter(is_active=True).order_by('sort_order').first()
        if first_media and first_media.file:
            media_url = first_media.file.url

        return CampaignMessage(
            recipient=recipient,
            subject=campaign.title,
            body="\n".join(lines),
            media_url=media_url,
        )

    @staticmethod
    @transaction.atomic
    def dispatch(campaign: MarketingCampaign, recipient: str, media_url: str = None, channels: list = None):
        """
        Enqueues async tasks for each selected channel in the campaign.
        Called from the API view; returns immediately (202 pattern).

        `channels`: subconjunto opcional de `campaign.channels` a despachar (default: todos).
        Agregado en Fase 17-18 (2026-09-23, PLAN_SINTEL_MARKETING_CAMPANAS_..._LOOP.md) para que
        el endpoint manual "Enviar ahora" pueda separar canales de broadcast (recipient=
        "broadcast") de canales directos (recipient real) en 2 llamadas sin disparar dos veces
        el mismo canal con un recipient distinto -- `marketing/agent/brain.py` sigue llamando
        sin este argumento, comportamiento idéntico al de antes (default: todos los canales).
        """
        from marketing.tasks import send_via_channel_task

        for channel in (channels if channels is not None else campaign.channels):
            if channel == 'whatsapp' and _marketing_whatsapp_rate_limited():
                logger.warning(
                    "[MarketingCommands] whatsapp omitido por rate-limit (comparte cuota Meta "
                    "con soporte transaccional) -- campaign=%s", campaign.uuid,
                )
                continue

            log, created = CampaignLog.objects.get_or_create(
                campaign=campaign,
                channel=channel,
                recipient=recipient,
            )
            if log.is_sent:
                continue  # Idempotency: skip already-sent logs

            logger.info("marketing_event=channel_send_started campaign=%s channel=%s log=%s",
                        campaign.uuid, channel, log.uuid)
            send_via_channel_task.delay(
                campaign_id=str(campaign.uuid),
                channel=channel,
                recipient=recipient,
                media_url=media_url,
                log_id=str(log.uuid),
            )

    @staticmethod
    @transaction.atomic
    def send_now(log_id: str):
        """
        Executes a single CampaignLog send. Called by Celery worker.
        """
        log = CampaignLog.objects.select_related('campaign').get(uuid=log_id)
        if log.is_sent:
            return

        campaign = log.campaign
        message = MarketingCommands.build_message(campaign, log.recipient)

        adapter = get_adapter(log.channel)
        result = adapter.send(message)

        log.is_sent = result["success"]
        log.sent_at = timezone.now() if result["success"] else None
        log.error_message = result["response"] if not result["success"] else ""
        log.save()
        if result["success"]:
            logger.info("marketing_event=channel_send_success campaign=%s channel=%s log=%s",
                        campaign.uuid, log.channel, log.uuid)
        else:
            logger.warning("marketing_event=channel_send_failed campaign=%s channel=%s log=%s error=%s",
                           campaign.uuid, log.channel, log.uuid, log.error_message)


# PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 12/13 (2026-09-23).
# Sin libreria de MIME de terceros en el proyecto (confirmado, ver docstring de CampaignMedia) --
# Pillow (dependencia YA existente, la usa django.db.models.ImageField en todo el proyecto) es
# suficiente para verificar que una IMAGEN es real (decodifica su contenido real, no solo lee la
# extension) y leer sus dimensiones reales. Para VIDEO no hay libreria de metadata disponible
# (ffmpeg-python/moviepy/pymediainfo ausentes de requirements.txt) -- se valida MIME/extension/
# tamano, NO duracion/dimensiones (gap documentado a proposito, ver MARKETING_GAPS.md).
CAMPAIGN_MEDIA_ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
CAMPAIGN_MEDIA_ALLOWED_VIDEO_CONTENT_TYPES = {'video/mp4'}
CAMPAIGN_MEDIA_ALLOWED_VIDEO_EXTENSIONS = {'.mp4'}


class CampaignMediaValidationError(Exception):
    """Error de validacion real de archivo -- el caller (serializer/view) lo traduce a 400."""


def _sha256_of(file_obj) -> str:
    file_obj.seek(0)
    digest = hashlib.sha256()
    for chunk in file_obj.chunks() if hasattr(file_obj, 'chunks') else iter(lambda: file_obj.read(8192), b''):
        digest.update(chunk)
    file_obj.seek(0)
    return digest.hexdigest()


def _validate_and_probe_image(file_obj) -> dict:
    from PIL import Image, UnidentifiedImageError

    max_bytes = settings.MARKETING_MEDIA_MAX_IMAGE_MB * 1024 * 1024
    if file_obj.size > max_bytes:
        raise CampaignMediaValidationError(
            f'La imagen supera el tamano maximo permitido ({settings.MARKETING_MEDIA_MAX_IMAGE_MB} MB).'
        )
    file_obj.seek(0)
    try:
        img = Image.open(file_obj)
        img.verify()  # decodifica y confirma que es una imagen real, no solo la extension/MIME declarado
    except (UnidentifiedImageError, OSError):
        raise CampaignMediaValidationError('El archivo no es una imagen valida (JPG/PNG/WEBP).')
    if img.format not in CAMPAIGN_MEDIA_ALLOWED_IMAGE_FORMATS:
        raise CampaignMediaValidationError(
            f'Formato de imagen no soportado ({img.format}). Formatos validos: JPG, PNG, WEBP.'
        )
    # Image.verify() invalida el objeto para mas operaciones -- reabrir para leer dimensiones reales.
    file_obj.seek(0)
    width, height = Image.open(file_obj).size
    file_obj.seek(0)
    return {
        'mime_type': f'image/{img.format.lower()}',
        'width': width,
        'height': height,
        'duration': None,
    }


def _validate_and_probe_video(file_obj) -> dict:
    import os

    max_bytes = settings.MARKETING_MEDIA_MAX_VIDEO_MB * 1024 * 1024
    if file_obj.size > max_bytes:
        raise CampaignMediaValidationError(
            f'El video supera el tamano maximo permitido ({settings.MARKETING_MEDIA_MAX_VIDEO_MB} MB).'
        )
    ext = os.path.splitext(getattr(file_obj, 'name', '') or '')[1].lower()
    if ext not in CAMPAIGN_MEDIA_ALLOWED_VIDEO_EXTENSIONS:
        raise CampaignMediaValidationError('Extension de video no soportada. Formato valido: MP4.')
    content_type = (getattr(file_obj, 'content_type', '') or '').lower()
    if content_type and content_type not in CAMPAIGN_MEDIA_ALLOWED_VIDEO_CONTENT_TYPES:
        raise CampaignMediaValidationError(
            f'Tipo de archivo no soportado ({content_type}). Formato valido: MP4 (video/mp4).'
        )
    # Sin libreria de metadata de video disponible en el proyecto -- width/height/duration
    # quedan sin poblar a proposito (gap documentado, ver docstring del modulo y MARKETING_GAPS.md).
    return {
        'mime_type': content_type or 'video/mp4',
        'width': None,
        'height': None,
        'duration': None,
    }


class CampaignMediaCommands:
    """Mismo patron que shop.services.commands.ProductImageCommands (add_image/delete_image/
    set_primary_image) -- extendido con la validacion real que el plan exige (Fase 12/13)."""

    @staticmethod
    @transaction.atomic
    def add_media(campaign: MarketingCampaign, file_obj, media_type: str) -> CampaignMedia:
        if media_type == CampaignMedia.TYPE_IMAGE:
            probe = _validate_and_probe_image(file_obj)
        elif media_type == CampaignMedia.TYPE_VIDEO:
            probe = _validate_and_probe_video(file_obj)
        else:
            raise CampaignMediaValidationError(f'media_type invalido: {media_type!r}.')

        file_hash = _sha256_of(file_obj)
        next_order = (
            CampaignMedia.objects.filter(campaign=campaign).count()
        )
        logger.info("marketing_event=media_uploaded campaign=%s type=%s size=%s hash=%s",
                    campaign.uuid, media_type, file_obj.size, file_hash)
        return CampaignMedia.objects.create(
            campaign=campaign,
            media_type=media_type,
            file=file_obj,
            mime_type=probe['mime_type'],
            size=file_obj.size,
            width=probe['width'],
            height=probe['height'],
            duration=probe['duration'],
            file_hash=file_hash,
            sort_order=next_order,
        )

    @staticmethod
    @transaction.atomic
    def delete_media(campaign: MarketingCampaign, media_uuid):
        media = CampaignMedia.objects.get(uuid=media_uuid, campaign=campaign)
        media.delete()
        logger.info("marketing_event=media_removed campaign=%s media=%s", campaign.uuid, media_uuid)

    @staticmethod
    @transaction.atomic
    def toggle_active(campaign: MarketingCampaign, media_uuid) -> CampaignMedia:
        media = CampaignMedia.objects.get(uuid=media_uuid, campaign=campaign)
        media.is_active = not media.is_active
        media.save(update_fields=['is_active'])
        return media

    @staticmethod
    @transaction.atomic
    def reorder(campaign: MarketingCampaign, ordered_uuids: list) -> None:
        """`ordered_uuids` es la lista completa de uuids de la galeria en el nuevo orden --
        mismo criterio de reordenamiento por lista completa que otros managers del proyecto."""
        media_by_uuid = {str(m.uuid): m for m in CampaignMedia.objects.filter(campaign=campaign)}
        for position, media_uuid in enumerate(ordered_uuids):
            media = media_by_uuid.get(str(media_uuid))
            if media is None:
                raise CampaignMediaValidationError(f'Media {media_uuid} no pertenece a esta campana.')
            if media.sort_order != position:
                media.sort_order = position
                media.save(update_fields=['sort_order'])
