"""
Webhook entrante de WhatsApp (Meta Cloud API) -- Fase 7 AI Core, endurecido en
la FASE 5/6 del plan de integracion Meta Business
(Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).

Flujo: mensaje del cliente en WhatsApp -> Meta -> este webhook -> tarea
Celery (cola notifications) -> Action Graph (via support.ai_bridge, con
token acunado por Django) -> respuesta por WhatsApp (send_text, ventana de
servicio de 24h abierta por el mensaje entrante).

El endpoint hace solo 5 cosas (nada de logica de negocio pesada, nada de IA
dentro del request):
  1. validar el challenge (GET) con WHATSAPP_WEBHOOK_VERIFY_TOKEN
  2. validar la firma X-Hub-Signature-256 (fail-closed)
  3. persistir un MetaWebhookEvent por cada evento (incl. los rechazados)
  4. deduplicar por message_id (Redis cache.add, atomico)
  5. encolar la tarea Celery y responder 200 rapido

GET  = verificacion del webhook (hub.challenge).
POST = eventos entrantes. AllowAny (Meta no envia credenciales), igual que
       el webhook de Wompi.
"""
import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from marketing.integrations.meta.signatures import verify_meta_webhook_signature
from notifications.models import MetaWebhookEvent

logger = logging.getLogger(__name__)

# Meta reintrega el mismo webhook si no recibe 200 a tiempo (timeouts,
# picos de carga) -- sin dedupe, un reintento dispararia process_whatsapp_inbound_task
# de nuevo, consultaria a la IA otra vez y mandaria una respuesta duplicada
# por WhatsApp. TTL generoso (Meta reintenta durante horas, no dias, en sus
# escenarios documentados) via el mismo cache (Redis) que ya usa
# _channel_rate_limited() en notifications/services/commands.py.
_INBOUND_DEDUPE_TIMEOUT_SECONDS = 60 * 60 * 24

# Tope de tamano del payload que se guarda parseado en MetaWebhookEvent.payload
# para un evento con firma INVALIDA (forense sin abrir un vector de abuso con
# cuerpos gigantes falsificados). Los eventos validos se guardan completos.
_REJECTED_PAYLOAD_MAX_BYTES = 50_000


class WhatsAppInboundWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        mode = request.query_params.get('hub.mode', '')
        token = request.query_params.get('hub.verify_token', '')
        challenge = request.query_params.get('hub.challenge', '')
        expected = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        if mode == 'subscribe' and expected and token == expected:
            return HttpResponse(challenge, content_type='text/plain')
        return Response({'error': 'Verificacion invalida.'}, status=403)

    def post(self, request):
        raw_body = request.body
        payload_hash = hashlib.sha256(raw_body or b'').hexdigest()
        signature_ok = verify_meta_webhook_signature(
            settings.META_APP_SECRET,
            raw_body,
            request.headers.get('X-Hub-Signature-256', ''),
        )

        if not signature_ok:
            logger.warning('[whatsapp-webhook] firma invalida o ausente -- 403')
            forensic_payload = {}
            if raw_body and len(raw_body) <= _REJECTED_PAYLOAD_MAX_BYTES:
                try:
                    forensic_payload = request.data
                except Exception:
                    forensic_payload = {}
            MetaWebhookEvent.objects.create(
                object_type=MetaWebhookEvent.OBJECT_UNKNOWN,
                payload_hash=payload_hash,
                signature_valid=False,
                status=MetaWebhookEvent.STATUS_REJECTED,
                error_code='invalid_signature',
                payload=forensic_payload if isinstance(forensic_payload, dict) else {},
            )
            return Response({'error': 'Firma invalida.'}, status=403)

        from notifications.tasks import process_whatsapp_inbound_task
        try:
            for entry in (request.data.get('entry') or []):
                waba_id = str(entry.get('id', '')).strip()
                for change in (entry.get('changes') or []):
                    value = change.get('value') or {}
                    field = str(change.get('field', '')).strip()
                    phone_number_id = str(
                        (value.get('metadata') or {}).get('phone_number_id', '')
                    ).strip()

                    # -- callbacks de estado (delivered / read / failed) --------
                    for status_obj in (value.get('statuses') or []):
                        MetaWebhookEvent.objects.create(
                            object_type=MetaWebhookEvent.OBJECT_WHATSAPP,
                            event_type='statuses',
                            waba_id=waba_id,
                            phone_number_id=phone_number_id,
                            external_message_id=str(status_obj.get('id', '')).strip(),
                            payload_hash=payload_hash,
                            signature_valid=True,
                            status=MetaWebhookEvent.STATUS_RECEIVED,
                            error_code=str(status_obj.get('status', '')).strip()[:64],
                            payload=status_obj,
                        )

                    # -- mensajes entrantes ------------------------------------
                    for message in (value.get('messages') or []):
                        msg_type = message.get('type')
                        wa_id = str(message.get('from', '')).strip()
                        message_id = str(message.get('id', '')).strip()

                        if msg_type != 'text':
                            # Fase 9 (AUDITORIA/24): antes se descartaba sin rastro.
                            logger.info(
                                '[whatsapp-webhook] mensaje tipo "%s" ignorado (no soportado) de %s',
                                msg_type, wa_id,
                            )
                            MetaWebhookEvent.objects.create(
                                object_type=MetaWebhookEvent.OBJECT_WHATSAPP,
                                event_type=field or 'messages',
                                waba_id=waba_id,
                                phone_number_id=phone_number_id,
                                external_message_id=message_id,
                                payload_hash=payload_hash,
                                signature_valid=True,
                                status=MetaWebhookEvent.STATUS_FAILED,
                                error_code='unsupported_message_type',
                                payload=message,
                            )
                            continue

                        text = str((message.get('text') or {}).get('body', '')).strip()
                        if not (wa_id and text):
                            continue

                        is_new = True
                        if message_id:
                            # cache.add() es atomico: si la clave ya existe (mismo
                            # message_id ya visto), devuelve False sin sobreescribir
                            # -- evita la ventana de carrera de un get()+set()
                            # separado ante dos entregas casi simultaneas.
                            is_new = cache.add(
                                f'whatsapp_inbound_msg:{message_id}',
                                True,
                                timeout=_INBOUND_DEDUPE_TIMEOUT_SECONDS,
                            )
                        else:
                            logger.warning(
                                '[whatsapp-webhook] mensaje sin "id" -- no se puede '
                                'deduplicar, se procesa igual.'
                            )

                        event = MetaWebhookEvent.objects.create(
                            object_type=MetaWebhookEvent.OBJECT_WHATSAPP,
                            event_type=field or 'messages',
                            waba_id=waba_id,
                            phone_number_id=phone_number_id,
                            external_message_id=message_id,
                            payload_hash=payload_hash,
                            signature_valid=True,
                            status=(
                                MetaWebhookEvent.STATUS_RECEIVED if is_new
                                else MetaWebhookEvent.STATUS_DUPLICATE
                            ),
                            payload=message,
                        )

                        if not is_new:
                            logger.info(
                                '[whatsapp-webhook] mensaje %s ya procesado, se ignora '
                                'reintento de Meta.', message_id,
                            )
                            continue

                        process_whatsapp_inbound_task.delay(
                            wa_id=wa_id, text=text, event_id=event.id,
                        )
        except Exception:
            # Nunca devolver 5xx a Meta por un payload inesperado (reintenta
            # en loop) -- se registra y se responde 200.
            logger.exception('[whatsapp-webhook] payload inesperado')
        return Response({'status': 'ok'})
