import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)

# Fase 11 AI Core (Proactividad): dias sin respuesta desde que la cotizacion
# paso a ENVIADA antes de que el asistente escriba proactivamente al cliente.
_WITHOUT_RESPONSE_THRESHOLD_DAYS = 3
_PROACTIVE_SLUG = 'cotizacion_sin_respuesta'


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
    name='quotes.send_quotation_email',
    queue='notifications',
    acks_late=True,
)
def send_quotation_email_task(self, quotation_uuid: str):
    """
    Generate the quotation PDF and send it by email to the client.
    Triggered automatically when a Quotation transitions to SENT status.
    """
    from quotes.models import Quotation
    from quotes.services.pdf_service import PDFService

    try:
        quotation = Quotation.objects.prefetch_related(
            'items__cost_snapshots',
            'services__materials',
            'rental_items',
        ).get(uuid=quotation_uuid, is_deleted=False)
    except Quotation.DoesNotExist:
        logger.error("send_quotation_email_task: Quotation %s not found.", quotation_uuid)
        return

    pdf_buffer = PDFService.generate_quotation_pdf(quotation)
    filename = f"cotizacion_{quotation.uuid}.pdf"

    email = EmailMessage(
        subject=f"Presupuesto Sintel Technology - {quotation.client_name}",
        body=(
            f"Estimado/a {quotation.client_name},\n\n"
            "Adjunto encontrara el presupuesto solicitado. "
            "Cualquier consulta puede comunicarse con nosotros.\n\n"
            "Sintel Technology\n"
            "sintel.technology@gmail.com"
        ),
        to=[quotation.client_email],
    )
    email.attach(filename, pdf_buffer.read(), 'application/pdf')
    email.send(fail_silently=False)

    logger.info("Quotation %s emailed to %s.", quotation_uuid, quotation.client_email)


@shared_task
def notify_quotations_without_response() -> None:
    """
    Fase 11 AI Core (Proactividad): cotizaciones en ENVIADA sin transicion a
    ACEPTADA/RECHAZADA por _WITHOUT_RESPONSE_THRESHOLD_DAYS -- el asistente
    deja un mensaje proactivo en la sala de soporte del cliente via el Event
    Bus (NotificationCommands.dispatch_notification -> AI_PROACTIVE_SLUGS).
    Cotizaciones anonimas (sin user) se excluyen -- no hay sala de chat a
    donde escribirles. Dedupe por NotificationLog: cada cotizacion se notifica
    una sola vez.
    """
    from notifications.services.commands import NotificationCommands
    from quotes.models import Quotation

    cutoff = timezone.now() - timedelta(days=_WITHOUT_RESPONSE_THRESHOLD_DAYS)
    candidates = Quotation.objects.filter(
        status=Quotation.STATUS_SENT,
        updated_at__lt=cutoff,
        user__isnull=False,
        is_deleted=False,
    )

    notified = 0
    for quotation in candidates:
        sent = NotificationCommands.dispatch_notification_once(
            user=quotation.user,
            template_slug=_PROACTIVE_SLUG,
            context={'quotation_uuid': str(quotation.uuid), 'status': quotation.status},
            dedupe_key=f'quotation:{quotation.uuid}',
        )
        if sent:
            notified += 1

    if notified:
        logger.info(
            "notify_quotations_without_response: %s cotizacion(es) notificada(s) "
            "(sin respuesta desde antes de %s)", notified, cutoff,
        )
