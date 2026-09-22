"""
notifications/api/whatsapp_gateway_webhook.py

Fase 6/7 de PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md -- receptor real
del Event Bus `whatsapp_gateway/` (Node/Baileys) -> Django. Mismo patron y
misma ubicacion que `whatsapp_webhook.py` (el receptor de Meta Cloud API) --
ambos son puntos de entrada de transporte para el mismo dominio `whatsapp/`,
uno por proveedor.

## Alcance real (Fase 6/8) -- que SI hace y que NO hace todavia

Este endpoint autentica, valida forma y deduplica (para `message.received`,
reusando `WhatsAppIdempotencyGuard`, canal `"baileys"` -- provider-agnostic
por diseno, ver whatsapp/domain/idempotency.py). Registra evidencia
estructurada en logs para cada evento.

Fase 8: `message.received` SI encola `process_whatsapp_gateway_inbound_task`
(notifications/tasks.py) -- pero UNICAMENTE si
`settings.WHATSAPP_CONNECTION_TYPE == 'QR_WEB_SESSION'`. Razon real: esa
tarea construye `WhatsAppService(WhatsAppConnectionFactory.create())`, que
resuelve el adapter de RESPUESTA segun ese mismo setting -- si el mecanismo
activo fuera otro (`META_CLOUD_API`, el default real de produccion hoy),
la respuesta de la IA saldria por el adapter equivocado (un numero de
WhatsApp distinto al que efectivamente recibio el mensaje). Mientras ese
guard no se cumpla, el evento se autentica/deduplica/audita igual pero NO
se procesa como negocio real -- mismo criterio "fail-loud, nunca simulado"
que ya aplica en `whatsapp/adapters/qr_web_session_adapter.py`.

No se crea ningun modelo nuevo para persistir estos eventos (Fase 31,
prohibido explicitamente "inventar modelos") -- logs estructurados son la
auditoria de este pase, igual que `MetaWebhookEvent` lo es para el canal
REST, pero sin duplicar esa tabla para un canal que reusa la infraestructura
de idempotencia/dominio ya existente.
"""
import logging

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from whatsapp.domain.idempotency import WhatsAppIdempotencyGuard

logger = logging.getLogger("whatsapp.gateway_webhook")

_VALID_EVENTS = {
    "whatsapp.connection.status",
    "whatsapp.connection.qr",
    "whatsapp.connection.logged_out",
    "whatsapp.message.received",
    "whatsapp.message.sent",
    "whatsapp.message.failed",
}

_CHANNEL = "baileys"


def _broadcast_to_admins(ws_type: str, payload: dict) -> None:
    """Fase 17: reusa el mismo canal/grupo que ya transmite el chat de
    soporte a los admins conectados (support/consumers.py::SupportChatConsumer,
    grupo 'support_admins') -- mismo patron que
    whatsapp/domain/service.py::WhatsAppService._broadcast. `layer is None`
    en tests/entornos sin Channels configurado -- no-op silencioso, mismo
    criterio que ese metodo."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)("support_admins", {"type": ws_type, **payload})


class WhatsAppGatewayEventView(APIView):
    """AllowAny + auth manual por header -- mismo patron que
    WhatsAppInboundWebhookView (Meta no manda credenciales DRF estandar,
    el gateway tampoco; ambos se autentican con su propio mecanismo, no
    con el sistema de auth de usuarios)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.headers.get("X-Gateway-Token", "")
        expected = settings.WHATSAPP_GATEWAY_TOKEN
        if not expected or token != expected:
            logger.warning("[whatsapp.gateway_webhook] token invalido o ausente -- 401")
            return Response({"error": "token invalido o ausente (X-Gateway-Token)"}, status=401)

        try:
            payload = request.data if isinstance(request.data, dict) else {}
            event_type = str(payload.get("event", "")).strip()

            if event_type not in _VALID_EVENTS:
                logger.warning("[whatsapp.gateway_webhook] evento desconocido: %r", event_type)
                return Response({"error": f"evento desconocido: {event_type!r}"}, status=400)

            event_id = str(payload.get("event_id", "")).strip()

            if event_type == "whatsapp.message.received":
                message = payload.get("message") or {}
                provider_message_id = str(message.get("provider_message_id", "")).strip()
                is_duplicate = False
                if provider_message_id:
                    is_duplicate = WhatsAppIdempotencyGuard.is_duplicate(_CHANNEL, provider_message_id)
                else:
                    logger.warning(
                        "[whatsapp.gateway_webhook] message.received sin provider_message_id -- no se puede deduplicar"
                    )

                if is_duplicate:
                    logger.info(
                        "[whatsapp.gateway_webhook] mensaje %s ya procesado, se ignora reintento",
                        provider_message_id,
                    )
                    return Response({"status": "duplicate"})

                if settings.WHATSAPP_CONNECTION_TYPE != "QR_WEB_SESSION":
                    logger.info(
                        "[whatsapp.gateway_webhook] message.received event_id=%s provider_message_id=%s "
                        "-- NO se procesa (WHATSAPP_CONNECTION_TYPE=%r != QR_WEB_SESSION, ver docstring del modulo)",
                        event_id, provider_message_id, settings.WHATSAPP_CONNECTION_TYPE,
                    )
                    return Response({"status": "received_not_processed", "reason": "connection_type_mismatch"})

                sender_phone = str(message.get("sender_phone", "")).strip()
                text = str(message.get("text", "")).strip()
                remote_jid = str(message.get("remote_jid", "")).strip()
                if not (sender_phone and text):
                    logger.warning(
                        "[whatsapp.gateway_webhook] message.received event_id=%s sin sender_phone/text -- se ignora",
                        event_id,
                    )
                    return Response({"status": "received_not_processed", "reason": "missing_fields"})

                from notifications.tasks import process_whatsapp_gateway_inbound_task
                process_whatsapp_gateway_inbound_task.delay(
                    remote_jid=remote_jid,
                    sender_phone=sender_phone,
                    text=text,
                    provider_message_id=provider_message_id,
                )
                logger.info(
                    "[whatsapp.gateway_webhook] message.received event_id=%s provider_message_id=%s -- encolado",
                    event_id, provider_message_id,
                )
                return Response({"status": "received_processing"})

            # connection.status / connection.qr / connection.logged_out: Fase 17,
            # distribucion real al panel admin via el WebSocket de soporte YA
            # existente (grupo 'support_admins', ver support/consumers.py).
            # message.sent / message.failed: solo auditoria en logs por ahora --
            # el plan (Fase 17) no los lista entre los 3 eventos que el frontend
            # necesita (whatsapp.status/whatsapp.qr/whatsapp.error).
            if event_type in ("whatsapp.connection.status", "whatsapp.connection.logged_out"):
                _broadcast_to_admins("whatsapp.status", {
                    "status": payload.get("status") or ("LOGGED_OUT" if event_type.endswith("logged_out") else None),
                    "phone": payload.get("phone"),
                    "jid": payload.get("jid"),
                })
            elif event_type == "whatsapp.connection.qr":
                _broadcast_to_admins("whatsapp.qr", {"qr_image": payload.get("qr_image")})

            logger.info(
                "[whatsapp.gateway_webhook] %s event_id=%s",
                event_type, event_id,
            )
            return Response({"status": "logged"})
        except Exception:
            # Mismo criterio que el webhook de Meta: nunca devolver 5xx por un
            # payload inesperado del gateway (evita reintentos en loop del
            # lado del gateway si algun dia implementa retry).
            logger.exception("[whatsapp.gateway_webhook] payload inesperado")
            return Response({"status": "error_logged"})
