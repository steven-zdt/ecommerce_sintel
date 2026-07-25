"""
Webhook entrante de WhatsApp (Meta Cloud API) — Fase 7 AI Core.

Flujo: mensaje del cliente en WhatsApp -> Meta -> este webhook -> tarea
Celery (cola notifications) -> Action Graph (via support.ai_bridge, con
token acunado por Django) -> respuesta por WhatsApp (send_text, ventana de
servicio de 24h abierta por el mensaje entrante).

GET  = verificacion del webhook (hub.challenge) con
       WHATSAPP_WEBHOOK_VERIFY_TOKEN.
POST = eventos entrantes. AllowAny (Meta no envia credenciales), igual que
       el webhook de Wompi; responde 200 rapido y procesa async.
"""
import hashlib
import hmac
import logging

from django.conf import settings
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class WhatsAppInboundWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _signature_valid(self, request):
        """Verifica X-Hub-Signature-256 (HMAC-SHA256 del cuerpo crudo con el
        App Secret de Meta). Fail-CLOSED: si falta META_APP_SECRET se rechaza
        el evento -- no se repite el fail-open del webhook de Wompi (F-01).

        Se lee request.body antes que request.data para no gatillar el
        RawPostDataException de Django (una vez parseado el body no se puede
        volver a leer crudo).
        """
        secret = getattr(settings, 'META_APP_SECRET', '')
        if not secret:
            logger.critical(
                '[whatsapp-webhook] META_APP_SECRET no configurado -- evento rechazado.'
            )
            return False
        received = request.headers.get('X-Hub-Signature-256', '')
        expected = 'sha256=' + hmac.new(
            secret.encode('utf-8'), request.body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(received, expected)

    def get(self, request):
        mode = request.query_params.get('hub.mode', '')
        token = request.query_params.get('hub.verify_token', '')
        challenge = request.query_params.get('hub.challenge', '')
        expected = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        if mode == 'subscribe' and expected and token == expected:
            return HttpResponse(challenge, content_type='text/plain')
        return Response({'error': 'Verificacion invalida.'}, status=403)

    def post(self, request):
        if not self._signature_valid(request):
            logger.warning('[whatsapp-webhook] firma invalida o ausente -- 403')
            return Response({'error': 'Firma invalida.'}, status=403)
        from notifications.tasks import process_whatsapp_inbound_task
        try:
            for entry in (request.data.get('entry') or []):
                for change in (entry.get('changes') or []):
                    value = change.get('value') or {}
                    for message in (value.get('messages') or []):
                        if message.get('type') != 'text':
                            continue
                        wa_id = str(message.get('from', '')).strip()
                        text = str((message.get('text') or {}).get('body', '')).strip()
                        if wa_id and text:
                            process_whatsapp_inbound_task.delay(wa_id=wa_id, text=text)
        except Exception:
            # Nunca devolver 5xx a Meta por un payload inesperado (reintenta
            # en loop) -- se registra y se responde 200.
            logger.exception('[whatsapp-webhook] payload inesperado')
        return Response({'status': 'ok'})
