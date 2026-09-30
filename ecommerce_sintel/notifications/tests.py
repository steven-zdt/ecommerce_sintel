import hashlib
import hmac
import uuid
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from notifications.models import (
    NotificationTemplate, NotificationLog, UserNotificationPreference,
    MetaWebhookEvent,
    CHANNEL_EMAIL, CHANNEL_WHATSAPP, CHANNEL_WEB_SOCKET
)
from notifications.services.commands import NotificationCommands
from notifications.clients.whatsapp import (
    WhatsAppClient, WhatsAppApiError, WhatsAppAuthError, WhatsAppConfigError
)
from notifications.tasks import (
    send_ws_notification_task, send_email_notification_task, send_whatsapp_notification_task,
    process_whatsapp_inbound_task,
)

User = get_user_model()


class NotificationsTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()

        # Create user
        self.user = User.objects.create_user(
            email="notify_user@example.com",
            password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

        # Create active notification template
        self.template = NotificationTemplate.objects.create(
            slug="order-update",
            name="Order Update Template",
            subject="Order {{ order_id }} Update",
            email_body="Hello, your order {{ order_id }} is now {{ status }}.",
            whatsapp_template_name="order_update_whatsapp",
            ws_event_type="ORDER_UPDATED",
            is_active=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # 1. NotificationCommands.dispatch_notification tests
    # ──────────────────────────────────────────────────────────────────────────

    @patch('notifications.tasks.send_ws_notification_task.delay')
    @patch('notifications.tasks.send_email_notification_task.delay')
    @patch('notifications.tasks.send_whatsapp_notification_task.delay')
    def test_dispatch_all_channels_by_default(self, mock_wa, mock_email, mock_ws):
        # Setup user profile with Colombian phone number to trigger WhatsApp channel
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, phone_number="3001234567")


        context = {"order_id": "12345", "status": "shipped"}

        NotificationCommands.dispatch_notification(
            user=self.user,
            template_slug="order-update",
            context=context
        )

        mock_ws.assert_called_once_with(
            user_id=self.user.pk,
            template_slug="order-update",
            ws_group=f"user_{self.user.uuid}",
            event_type="ORDER_UPDATED",
            context=context
        )
        mock_email.assert_called_once_with(
            user_id=self.user.pk,
            template_slug="order-update",
            context=context
        )
        mock_wa.assert_called_once_with(
            user_id=self.user.pk,
            template_slug="order-update",
            phone="3001234567",
            context=context
        )

    @patch('notifications.tasks.send_ws_notification_task.delay')
    @patch('notifications.tasks.send_email_notification_task.delay')
    @patch('notifications.tasks.send_whatsapp_notification_task.delay')
    def test_dispatch_respects_user_preferences(self, mock_wa, mock_email, mock_ws):
        # User explicitly disabled WebSockets and WhatsApp, only wants Email
        UserNotificationPreference.objects.create(
            user=self.user,
            channel=CHANNEL_EMAIL,
            is_enabled=True
        )
        UserNotificationPreference.objects.create(
            user=self.user,
            channel=CHANNEL_WEB_SOCKET,
            is_enabled=False
        )
        UserNotificationPreference.objects.create(
            user=self.user,
            channel=CHANNEL_WHATSAPP,
            is_enabled=False
        )

        NotificationCommands.dispatch_notification(
            user=self.user,
            template_slug="order-update",
            context={"order_id": "123"}
        )

        mock_email.assert_called_once()
        mock_ws.assert_not_called()
        mock_wa.assert_not_called()

    @patch('notifications.tasks.send_ws_notification_task.delay')
    def test_dispatch_inactive_template_does_nothing(self, mock_ws):
        self.template.is_active = False
        self.template.save()

        NotificationCommands.dispatch_notification(
            user=self.user,
            template_slug="order-update",
            context={}
        )
        mock_ws.assert_not_called()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Celery Tasks tests
    # ──────────────────────────────────────────────────────────────────────────

    @patch('ecommerce.ws_notify.ws_notify')
    def test_send_ws_notification_task_success(self, mock_ws_notify):
        context = {"status": "paid"}
        send_ws_notification_task(
            user_id=self.user.pk,
            template_slug="order-update",
            ws_group="user_group",
            event_type="ORDER_UPDATED",
            context=context
        )

        mock_ws_notify.assert_called_once_with(
            group="user_group",
            event_type="ORDER_UPDATED",
            payload=context
        )

        # Log should exist with SENT status
        log = NotificationLog.objects.get(user=self.user, channel=CHANNEL_WEB_SOCKET)
        self.assertEqual(log.status, NotificationLog.STATUS_SENT)
        self.assertEqual(log.payload_context, context)

    @patch('django.core.mail.send_mail')
    def test_send_email_notification_task_success_and_subject_rendering(self, mock_send_mail):
        context = {"order_id": "999", "status": "cancelled"}
        send_email_notification_task(
            user_id=self.user.pk,
            template_slug="order-update",
            context=context
        )

        mock_send_mail.assert_called_once()
        kwargs = mock_send_mail.call_args[1]
        self.assertEqual(kwargs['subject'], "Order 999 Update")
        self.assertIn("Hello, your order 999 is now cancelled.", kwargs['message'])
        self.assertEqual(kwargs['recipient_list'], [self.user.email])

        log = NotificationLog.objects.get(user=self.user, channel=CHANNEL_EMAIL)
        self.assertEqual(log.status, NotificationLog.STATUS_SENT)

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_template')
    def test_send_whatsapp_notification_task_success(self, mock_send_template):
        send_whatsapp_notification_task(
            user_id=self.user.pk,
            template_slug="order-update",
            phone="3007654321",
            context={"status": "delivered"}
        )

        mock_send_template.assert_called_once_with(
            to="573007654321",
            template_name="order_update_whatsapp",
            variables={"status": "delivered"}
        )

        log = NotificationLog.objects.get(user=self.user, channel=CHANNEL_WHATSAPP)
        self.assertEqual(log.status, NotificationLog.STATUS_SENT)

    def test_tasks_graceful_missing_db_objects(self):
        # Test nonexistent user_id and template_slug does not raise exception/retry
        result_ws = send_ws_notification_task(
            user_id=9999,
            template_slug="order-update",
            ws_group="group",
            event_type="event",
            context={}
        )
        self.assertIsNone(result_ws)

        result_email = send_email_notification_task(
            user_id=self.user.pk,
            template_slug="nonexistent-slug",
            context={}
        )
        self.assertIsNone(result_email)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. WhatsApp Client configuration & API response tests
    # ──────────────────────────────────────────────────────────────────────────

    @override_settings(META_ACCESS_TOKEN='', WHATSAPP_PHONE_NUMBER_ID='')
    def test_whatsapp_client_missing_config_raises_custom_error(self):
        client = WhatsAppClient()
        with self.assertRaises(WhatsAppConfigError):
            client.send_template(
                to="573001234567",
                template_name="test",
                variables={}
            )

    # El transporte HTTP se movio a marketing/integrations/meta/client.py
    # (MetaGraphClient, FASE 3 integracion Meta Business). Estos 3 tests ahora
    # mockean ese seam unico (requests.request) en vez de requests.Session.post.
    @override_settings(META_ACCESS_TOKEN='valid_token', WHATSAPP_PHONE_NUMBER_ID='valid_phone_id')
    @patch('marketing.integrations.meta.client.requests.request')
    def test_whatsapp_client_send_template_auth_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": {"message": "Invalid OAuth Access Token", "code": 190}}'
        mock_response.json.return_value = {"error": {"message": "Invalid OAuth Access Token", "code": 190}}
        mock_request.return_value = mock_response

        client = WhatsAppClient()
        with self.assertRaises(WhatsAppAuthError):
            client.send_template(
                to="573001234567",
                template_name="test",
                variables={}
            )

    @override_settings(META_ACCESS_TOKEN='valid_token', WHATSAPP_PHONE_NUMBER_ID='valid_phone_id')
    @patch('marketing.integrations.meta.client.requests.request')
    def test_whatsapp_client_send_template_api_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = '{"error": {"message": "Internal Server Error"}}'
        mock_response.json.return_value = {"error": {"message": "Internal Server Error"}}
        mock_request.return_value = mock_response

        client = WhatsAppClient()
        with self.assertRaises(WhatsAppApiError):
            # Should not be WhatsAppAuthError
            try:
                client.send_template(
                    to="573001234567",
                    template_name="test",
                    variables={}
                )
            except WhatsAppAuthError:
                self.fail("Raised WhatsAppAuthError instead of general WhatsAppApiError")

    @override_settings(META_ACCESS_TOKEN='valid_token', WHATSAPP_PHONE_NUMBER_ID='valid_phone_id')
    @patch('marketing.integrations.meta.client.requests.request')
    def test_whatsapp_client_send_template_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"messages": [{"id": "wamid.HBgLNTczMDA0NTY3ODkwFQIAERg"}]}'
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.HBgLNTczMDA0NTY3ODkwFQIAERg"}]
        }
        mock_request.return_value = mock_response

        client = WhatsAppClient()
        msg_id = client.send_template(
            to="573001234567",
            template_name="test",
            variables={"var1": "val1"}
        )

        self.assertEqual(msg_id, "wamid.HBgLNTczMDA0NTY3ODkwFQIAERg")
        mock_request.assert_called_once()
        payload = mock_request.call_args[1]['json']
        self.assertEqual(payload['template']['components'][0]['parameters'][0]['text'], 'val1')

    # ──────────────────────────────────────────────────────────────────────────
    # 4. API Endpoint tests
    # ──────────────────────────────────────────────────────────────────────────

    def test_notification_log_viewset_uuid_lookup(self):
        log = NotificationLog.objects.create(
            user=self.user,
            template=self.template,
            channel=CHANNEL_EMAIL,
            status=NotificationLog.STATUS_SENT,
            payload_context={}
        )

        # Standard list endpoint
        list_url = reverse('notification-logs-list')
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        if isinstance(list_response.data, dict) and 'results' in list_response.data:
            self.assertEqual(len(list_response.data['results']), 1)
        else:
            self.assertEqual(len(list_response.data), 1)


        # Retrieve endpoint using UUID lookup_field
        detail_url = reverse('notification-logs-detail', kwargs={'uuid': str(log.uuid)})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['uuid'], str(log.uuid))

    def test_user_notification_preference_viewset(self):
        # 1. GET list preferences
        list_url = reverse('notification-preferences-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return list of all CHANNEL_CHOICES with is_enabled=True by default
        channels_in_response = [item['channel'] for item in response.data]
        self.assertIn(CHANNEL_EMAIL, channels_in_response)
        self.assertIn(CHANNEL_WHATSAPP, channels_in_response)
        self.assertIn(CHANNEL_WEB_SOCKET, channels_in_response)
        for item in response.data:
            self.assertTrue(item['is_enabled'])

        # 2. POST set preference to disable WhatsApp
        set_url = reverse('notification-preferences-set-preference')
        data = {
            "channel": CHANNEL_WHATSAPP,
            "is_enabled": False
        }
        response_post = self.client.post(set_url, data, format='json')
        self.assertEqual(response_post.status_code, status.HTTP_200_OK)
        self.assertFalse(response_post.data['is_enabled'])

        # Verify database record updated
        pref = UserNotificationPreference.objects.get(user=self.user, channel=CHANNEL_WHATSAPP)
        self.assertFalse(pref.is_enabled)

        # List should reflect this custom setting
        response_list = self.client.get(list_url)
        for item in response_list.data:
            if item['channel'] == CHANNEL_WHATSAPP:
                self.assertFalse(item['is_enabled'])
            else:
                self.assertTrue(item['is_enabled'])


@override_settings(META_APP_SECRET='test-meta-app-secret')
class WhatsAppInboundWebhookSignatureTestCase(TransactionTestCase):
    """
    Test de regresion para N-01 (auditoria enterprise, 2026-07-24).

    El webhook entrante de WhatsApp no verificaba X-Hub-Signature-256 -- cualquiera
    con la URL podia inyectar mensajes con un wa_id arbitrario y disparar el Action
    Graph de IA suplantando a un cliente real. La correccion es fail-CLOSED: sin
    META_APP_SECRET configurado, o con una firma que no calza, el evento se rechaza.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('whatsapp-inbound-webhook')
        self.body = b'{"entry": [{"changes": [{"value": {"messages": []}}]}]}'

    def _signed_headers(self, secret, body):
        signature = 'sha256=' + hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        return {'HTTP_X_HUB_SIGNATURE_256': signature}

    def test_missing_signature_header_is_rejected(self):
        response = self.client.generic(
            'POST', self.url, data=self.body, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_signature_is_rejected(self):
        bad_headers = self._signed_headers('a-completely-different-secret', self.body)
        response = self.client.generic(
            'POST', self.url, data=self.body, content_type='application/json', **bad_headers
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_signature_is_accepted(self):
        good_headers = self._signed_headers('test-meta-app-secret', self.body)
        response = self.client.generic(
            'POST', self.url, data=self.body, content_type='application/json', **good_headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(META_APP_SECRET='')
    def test_missing_app_secret_fails_closed_even_with_a_signature(self):
        # Fail-CLOSED (F-01 no se repite aqui): sin secreto configurado, ni
        # siquiera una firma "valida" para un secreto viejo/adivinado debe pasar.
        headers = self._signed_headers('whatever-the-caller-guesses', self.body)
        response = self.client.generic(
            'POST', self.url, data=self.body, content_type='application/json', **headers
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(META_APP_SECRET='test-meta-app-secret')
class WhatsAppInboundWebhookDedupeTestCase(TransactionTestCase):
    """
    Test de regresion para el hallazgo de la auditoria de 2026-07-31: Meta
    reintrega el mismo webhook si no recibe 200 a tiempo -- sin dedupe por
    message.id, un reintento disparaba process_whatsapp_inbound_task() de
    nuevo (consulta a la IA + respuesta duplicada por WhatsApp).
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('whatsapp-inbound-webhook')

    def _signed_post(self, body: bytes):
        signature = 'sha256=' + hmac.new(b'test-meta-app-secret', body, hashlib.sha256).hexdigest()
        return self.client.generic(
            'POST', self.url, data=body, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

    def _payload(self, message_id: str) -> bytes:
        import json
        return json.dumps({
            'entry': [{'changes': [{'value': {'messages': [{
                'id': message_id,
                'type': 'text',
                'from': '573001234567',
                'text': {'body': 'hola'},
            }]}}]}]
        }).encode('utf-8')

    @patch('notifications.tasks.process_whatsapp_inbound_task.delay')
    def test_duplicate_message_id_is_processed_only_once(self, mock_delay):
        body = self._payload(f'wamid.{uuid.uuid4()}')
        response1 = self._signed_post(body)
        response2 = self._signed_post(body)  # mismo body -> mismo message_id, simula el reintento de Meta
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_delay.call_count, 1)

    @patch('notifications.tasks.process_whatsapp_inbound_task.delay')
    def test_different_message_ids_are_both_processed(self, mock_delay):
        self._signed_post(self._payload(f'wamid.{uuid.uuid4()}'))
        self._signed_post(self._payload(f'wamid.{uuid.uuid4()}'))
        self.assertEqual(mock_delay.call_count, 2)

    @patch('notifications.tasks.process_whatsapp_inbound_task.delay')
    def test_message_without_id_is_still_processed(self, mock_delay):
        # Robustez: si Meta alguna vez manda un mensaje sin "id" (no deberia
        # pasar segun su documentacion), no debe bloquearse -- solo pierde la
        # proteccion de dedupe para ESE mensaje puntual.
        import json
        body = json.dumps({
            'entry': [{'changes': [{'value': {'messages': [{
                'type': 'text', 'from': '573001234567', 'text': {'body': 'hola'},
            }]}}]}]
        }).encode('utf-8')
        response = self._signed_post(body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_delay.assert_called_once()


@override_settings(META_APP_SECRET='test-meta-app-secret')
class MetaWebhookEventAuditTestCase(TransactionTestCase):
    """FASE 6 integracion Meta Business: cada evento del webhook queda auditado
    en MetaWebhookEvent, incluso los rechazados por firma y los reintentos."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('whatsapp-inbound-webhook')

    def _sign(self, body: bytes) -> str:
        return 'sha256=' + hmac.new(b'test-meta-app-secret', body, hashlib.sha256).hexdigest()

    def _post(self, body: bytes, signed=True):
        headers = {'HTTP_X_HUB_SIGNATURE_256': self._sign(body)} if signed else {}
        return self.client.generic('POST', self.url, data=body, content_type='application/json', **headers)

    def _text_payload(self, message_id: str) -> bytes:
        import json
        return json.dumps({'entry': [{'id': 'WABA123', 'changes': [{'field': 'messages', 'value': {
            'metadata': {'phone_number_id': 'PN99'},
            'messages': [{'id': message_id, 'type': 'text', 'from': '573001234567', 'text': {'body': 'hola'}}],
        }}]}]}).encode('utf-8')

    @patch('notifications.tasks.process_whatsapp_inbound_task.delay')
    def test_valid_text_message_persists_received_event(self, _delay):
        mid = f'wamid.{uuid.uuid4()}'
        self.assertEqual(self._post(self._text_payload(mid)).status_code, status.HTTP_200_OK)
        event = MetaWebhookEvent.objects.get(external_message_id=mid)
        self.assertEqual(event.status, MetaWebhookEvent.STATUS_RECEIVED)
        self.assertEqual(event.object_type, MetaWebhookEvent.OBJECT_WHATSAPP)
        self.assertEqual(event.waba_id, 'WABA123')
        self.assertEqual(event.phone_number_id, 'PN99')
        self.assertTrue(event.signature_valid)
        _delay.assert_called_once()
        self.assertEqual(_delay.call_args[1]['event_id'], event.id)

    @patch('notifications.tasks.process_whatsapp_inbound_task.delay')
    def test_meta_retry_persists_duplicate_event_and_skips_task(self, _delay):
        body = self._text_payload(f'wamid.{uuid.uuid4()}')
        self._post(body)
        self._post(body)
        statuses = sorted(MetaWebhookEvent.objects.values_list('status', flat=True))
        self.assertEqual(statuses, [MetaWebhookEvent.STATUS_DUPLICATE, MetaWebhookEvent.STATUS_RECEIVED])
        self.assertEqual(_delay.call_count, 1)

    def test_invalid_signature_persists_rejected_event(self):
        resp = self._post(self._text_payload(f'wamid.{uuid.uuid4()}'), signed=False)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        event = MetaWebhookEvent.objects.get()
        self.assertEqual(event.status, MetaWebhookEvent.STATUS_REJECTED)
        self.assertFalse(event.signature_valid)
        self.assertEqual(event.error_code, 'invalid_signature')

    def test_purge_task_sanitizes_then_deletes_by_age(self):
        from datetime import timedelta
        from django.utils import timezone
        from notifications.tasks import purge_meta_webhook_events_task

        now = timezone.now()
        recent = MetaWebhookEvent.objects.create(status='RECEIVED', payload={'text': 'hola'})
        mid = MetaWebhookEvent.objects.create(status='PROCESSED', payload={'text': 'secreto'})
        old = MetaWebhookEvent.objects.create(status='PROCESSED', payload={'text': 'viejo'})
        # received_at es auto_now_add -> se fuerza con update() para el test.
        MetaWebhookEvent.objects.filter(pk=mid.pk).update(received_at=now - timedelta(days=45))
        MetaWebhookEvent.objects.filter(pk=old.pk).update(received_at=now - timedelta(days=200))

        result = purge_meta_webhook_events_task()

        self.assertEqual(result, {'deleted': 1, 'sanitized': 1})
        self.assertFalse(MetaWebhookEvent.objects.filter(pk=old.pk).exists())
        mid.refresh_from_db()
        self.assertEqual(mid.payload, {})
        recent.refresh_from_db()
        self.assertEqual(recent.payload, {'text': 'hola'})

    @patch('notifications.tasks.process_whatsapp_inbound_task.delay')
    def test_status_callback_persists_statuses_event(self, _delay):
        import json
        body = json.dumps({'entry': [{'id': 'WABA123', 'changes': [{'field': 'messages', 'value': {
            'metadata': {'phone_number_id': 'PN99'},
            'statuses': [{'id': 'wamid.X', 'status': 'delivered'}],
        }}]}]}).encode('utf-8')
        self.assertEqual(self._post(body).status_code, status.HTTP_200_OK)
        event = MetaWebhookEvent.objects.get(event_type='statuses')
        self.assertEqual(event.error_code, 'delivered')
        self.assertEqual(event.external_message_id, 'wamid.X')
        _delay.assert_not_called()


class WhatsAppInboundVisibilityTestCase(TransactionTestCase):
    """
    M2 (AUDITORIA/19_AUDITORIA_COMMUNICATION_CENTER_CANALES.md, 2026-08-01): antes
    process_whatsapp_inbound_task no dejaba ningun rastro en BD -- invisible para
    /panel/soporte y Customer 360. Ahora persiste ambos lados (cliente + IA) en la
    ChatRoom real del usuario, reusando ChatCommands.
    """

    def setUp(self):
        from accounts.models import UserProfile
        self.user = User.objects.create_user(email='wa.visibilidad@test.sintel', password='x')
        UserProfile.objects.create(user=self.user, phone_number='3001234567')

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    def test_mensaje_entrante_y_respuesta_ia_quedan_en_la_chatroom(self, mock_ask_ai, mock_send_text):
        from support.models import ChatRoom, ChatMessage

        mock_ask_ai.return_value = {
            'response': 'Claro, con gusto te ayudo.',
            'metrics': {'intent': 'unknown', 'duration_ms': 5},
        }

        process_whatsapp_inbound_task(wa_id='573001234567', text='hola, necesito ayuda')

        room = ChatRoom.objects.get(user=self.user)
        messages = list(ChatMessage.objects.filter(room=room).order_by('created_at'))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].sender_id, self.user.id)
        self.assertEqual(messages[0].message, 'hola, necesito ayuda')
        self.assertTrue(messages[1].is_from_agent)  # bot IA, no el cliente
        self.assertEqual(messages[1].message, 'Claro, con gusto te ayudo.')
        self.assertEqual(messages[1].ai_metrics, {'intent': 'unknown', 'duration_ms': 5})
        mock_send_text.assert_called_once_with('573001234567', 'Claro, con gusto te ayudo.')

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    def test_sin_respuesta_ia_igual_persiste_el_mensaje_del_cliente(self, mock_ask_ai, mock_send_text):
        # Motor caido/sin respuesta: el mensaje del cliente NO debe perderse solo porque
        # la IA no respondio -- sigue siendo visible para un agente humano despues.
        from support.models import ChatRoom, ChatMessage

        mock_ask_ai.return_value = None

        process_whatsapp_inbound_task(wa_id='573001234567', text='hola de nuevo')

        room = ChatRoom.objects.get(user=self.user)
        messages = list(ChatMessage.objects.filter(room=room))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'hola de nuevo')
        mock_send_text.assert_not_called()

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    def test_event_id_lifecycle_is_marked_processed(self, mock_ask_ai, mock_send_text):
        mock_ask_ai.return_value = {'response': 'listo', 'metrics': {}}
        event = MetaWebhookEvent.objects.create(
            object_type=MetaWebhookEvent.OBJECT_WHATSAPP,
            external_message_id='wamid.LC1',
            status=MetaWebhookEvent.STATUS_RECEIVED,
            signature_valid=True,
        )
        process_whatsapp_inbound_task(wa_id='573001234567', text='hola', event_id=event.id)
        event.refresh_from_db()
        self.assertEqual(event.status, MetaWebhookEvent.STATUS_PROCESSED)
        self.assertIsNotNone(event.processed_at)

    def test_event_id_none_is_a_safe_noop(self):
        # Las llamadas directas / de otros tests no pasan event_id -- no debe romper.
        with patch('support.services.ai_bridge.ask_ai', return_value=None):
            process_whatsapp_inbound_task(wa_id='573001234567', text='sin evento')


@override_settings(AI_SUPPORT_CHAT_ENABLED=True)
class WhatsAppInboundHandoffGateTestCase(TransactionTestCase):
    """
    Auditoria E2E AI Engine (2026-08-17): antes process_whatsapp_inbound_task llamaba a
    ask_ai() sin chequear is_ai_mode_active()/is_ai_rate_limited() de la sala -- un cliente
    cuyo chat web ya habia escalado a un humano (ai_paused=True) seguia recibiendo
    auto-respuestas de la IA si escribia por WhatsApp, sin que el agente se enterara. Ahora
    este canal respeta el mismo gate que SupportChatConsumer._ai_mode_active/_ai_rate_limited.
    """

    def setUp(self):
        from accounts.models import UserProfile
        from support.services.commands import ChatCommands
        self.user = User.objects.create_user(email='wa.handoff@test.sintel', password='x')
        UserProfile.objects.create(user=self.user, phone_number='3009876543')
        self.room = ChatCommands.get_or_create_room(self.user)

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    def test_ai_paused_bloquea_auto_respuesta_pero_persiste_mensaje(self, mock_ask_ai, mock_send_text):
        from support.models import ChatRoom, ChatMessage

        self.room.ai_paused = True
        self.room.save(update_fields=['ai_paused'])

        process_whatsapp_inbound_task(wa_id='573009876543', text='sigo esperando ayuda')

        mock_ask_ai.assert_not_called()
        mock_send_text.assert_not_called()
        room = ChatRoom.objects.get(user=self.user)
        messages = list(ChatMessage.objects.filter(room=room))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'sigo esperando ayuda')

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    def test_admin_asignado_bloquea_auto_respuesta(self, mock_ask_ai, mock_send_text):
        from support.models import ChatRoom, ChatMessage
        admin = User.objects.create_user(
            email='admin.wa.handoff@test.sintel', password='x', is_staff=True, is_superuser=True,
        )
        self.room.assigned_admin = admin
        self.room.save(update_fields=['assigned_admin'])

        process_whatsapp_inbound_task(wa_id='573009876543', text='hola de nuevo')

        mock_ask_ai.assert_not_called()
        room = ChatRoom.objects.get(user=self.user)
        self.assertEqual(ChatMessage.objects.filter(room=room).count(), 1)

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    @patch('support.services.ai_bridge.is_ai_rate_limited', return_value=True)
    def test_rate_limit_de_ia_bloquea_auto_respuesta_por_whatsapp(self, mock_rate_limited, mock_ask_ai, mock_send_text):
        from support.models import ChatRoom, ChatMessage

        process_whatsapp_inbound_task(wa_id='573009876543', text='una pregunta mas')

        mock_ask_ai.assert_not_called()
        room = ChatRoom.objects.get(user=self.user)
        self.assertEqual(ChatMessage.objects.filter(room=room).count(), 1)

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    @patch('support.services.ai_bridge.ask_ai')
    def test_sala_normal_si_llama_a_ask_ai(self, mock_ask_ai, mock_send_text):
        # Control positivo: sin ai_paused/admin/rate-limit, el flujo normal sigue intacto.
        from support.models import ChatRoom, ChatMessage
        mock_ask_ai.return_value = {'response': 'Con gusto.', 'metrics': {'intent': 'unknown'}}

        process_whatsapp_inbound_task(wa_id='573009876543', text='hola')

        mock_ask_ai.assert_called_once()
        room = ChatRoom.objects.get(user=self.user)
        self.assertEqual(ChatMessage.objects.filter(room=room).count(), 2)


class RealBusinessEmailTemplatesTestCase(TransactionTestCase):
    """
    Auditoria de Email en produccion (PLAN_AUDITORIA_EMAIL_PRODUCCION_SINTEL_LOOP.md, Fase 6,
    2026-09-23) -- guarda de regresion permanente del incidente real donde 'order_created',
    'order_paid', 'rental_cod_review_pending', 'rental_payment_conflict_customer' y
    'rental_payment_conflict_admin' fallaban silenciosamente en produccion desde julio 2026 por
    no tener NotificationTemplate sembrado (ver orders/migrations/0018_seed_order_lifecycle_
    templates.py y renting/migrations/0038_seed_cod_and_payment_conflict_templates.py). Los
    tests genericos de arriba (NotificationsTestCase) usan una plantilla fabricada
    ('order-update'), nunca las reales -- por eso el gap paso desapercibido en tests durante
    meses pese a tener cobertura amplia del pipeline generico.
    """

    REAL_TEMPLATE_CONTEXTS = {
        'order_created': {'order_uuid': 'o-1', 'status': 'pending', 'total': '150000', 'user_name': 'Juan'},
        'order_paid': {'order_uuid': 'o-1', 'status': 'paid', 'total': '150000', 'user_name': 'Juan'},
        'rental_cod_review_pending': {
            'request_uuid': 'r-1', 'equipment_name': 'Camara PTZ', 'grand_total': '90000', 'user_name': 'Ana',
        },
        'rental_payment_conflict_customer': {
            'request_uuid': 'r-1', 'equipment_name': 'Camara PTZ', 'grand_total': '90000', 'user_name': 'Ana',
        },
        'rental_payment_conflict_admin': {
            'request_uuid': 'r-1', 'equipment_name': 'Camara PTZ', 'grand_total': '90000', 'user_name': 'Ana',
        },
    }

    def setUp(self):
        # Las migraciones de datos (RunPython) de este proyecto NO se aplican al armar la BD de
        # tests (confirmado en vivo -- otros tests ya existentes, ej. DispatchNotificationOnceTestCase
        # via race conditions, dependen de esto). Se siembran aqui las 5 plantillas leyendo el
        # TEMPLATES real de cada migracion (import_module, mismo mecanismo que usa Django para
        # cargar migraciones) -- fuente unica de verdad, sin duplicar el copy a mano y sin riesgo
        # de que este test quede desincronizado si el contenido real cambia.
        from importlib import import_module
        self.user = User.objects.create_user(email='real_templates_user@example.com', password='x')
        order_templates = import_module(
            'orders.migrations.0018_seed_order_lifecycle_templates'
        ).TEMPLATES
        renting_templates = import_module(
            'renting.migrations.0038_seed_cod_and_payment_conflict_templates'
        ).TEMPLATES
        for data in order_templates + renting_templates:
            NotificationTemplate.objects.update_or_create(
                slug=data['slug'], defaults={k: v for k, v in data.items() if k != 'slug'},
            )

    def test_todas_las_plantillas_de_negocio_reales_existen_y_activas(self):
        for slug in self.REAL_TEMPLATE_CONTEXTS:
            with self.subTest(slug=slug):
                self.assertTrue(
                    NotificationTemplate.objects.filter(slug=slug, is_active=True).exists(),
                    f"'{slug}' no existe o esta inactiva -- algun caller real de "
                    f"dispatch_notification() la referencia y fallaria silenciosamente.",
                )

    def test_plantillas_de_negocio_reales_renderizan_sin_variables_rotas(self):
        from django.template import Template, Context
        for slug, ctx in self.REAL_TEMPLATE_CONTEXTS.items():
            with self.subTest(slug=slug):
                template = NotificationTemplate.objects.get(slug=slug)
                subject = Template(template.subject).render(Context(ctx))
                body = Template(template.email_body).render(Context(ctx))
                self.assertNotIn('{{', subject, f"'{slug}': subject con variable sin resolver")
                self.assertNotIn('{{', body, f"'{slug}': email_body con variable sin resolver")

    @patch('notifications.tasks.send_ws_notification_task.delay')
    @patch('notifications.tasks.send_email_notification_task.delay')
    @patch('notifications.tasks.send_whatsapp_notification_task.delay')
    def test_dispatch_notification_despacha_email_para_cada_plantilla_de_negocio_real(
        self, mock_wa, mock_email, mock_ws,
    ):
        for slug, ctx in self.REAL_TEMPLATE_CONTEXTS.items():
            with self.subTest(slug=slug):
                NotificationCommands.dispatch_notification(user=self.user, template_slug=slug, context=ctx)
                mock_email.assert_called_with(user_id=self.user.pk, template_slug=slug, context=ctx)

    def test_plantilla_de_negocio_inexistente_deja_notificationlog_failed_con_error_util(self):
        NotificationCommands.dispatch_notification(
            user=self.user, template_slug='slug_que_no_existe_de_verdad', context={},
        )
        log = NotificationLog.objects.get(user=self.user, template_slug='slug_que_no_existe_de_verdad')
        self.assertEqual(log.status, NotificationLog.STATUS_FAILED)
        self.assertTrue(log.error_message)


class DispatchNotificationOnceTestCase(TransactionTestCase):
    """
    Fase 9 (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-01).
    """

    def setUp(self):
        self.user = User.objects.create_user(email='dedupe_once@test.sintel', password='x')

    def test_no_crea_marcador_de_dedupe_si_la_plantilla_no_existe(self):
        sent = NotificationCommands.dispatch_notification_once(
            user=self.user,
            template_slug='slug_que_no_existe',
            context={'room_uuid': 'abc'},
            dedupe_key='chatroom:abc',
        )
        self.assertFalse(sent)
        self.assertFalse(
            NotificationLog.objects.filter(
                template_slug='slug_que_no_existe', channel='', payload_context__dedupe_key='chatroom:abc',
            ).exists()
        )

    def test_no_crea_marcador_de_dedupe_si_la_plantilla_esta_inactiva(self):
        NotificationTemplate.objects.create(
            slug='plantilla_inactiva', name='x', is_active=False,
            ws_event_type='X', email_body='x', subject='x',
        )
        sent = NotificationCommands.dispatch_notification_once(
            user=self.user,
            template_slug='plantilla_inactiva',
            context={},
            dedupe_key='entidad:1',
        )
        self.assertFalse(sent)
        self.assertFalse(
            NotificationLog.objects.filter(
                template_slug='plantilla_inactiva', channel='', payload_context__dedupe_key='entidad:1',
            ).exists()
        )

    @patch('notifications.tasks.send_ws_notification_task.delay')
    def test_reintenta_en_la_siguiente_corrida_si_la_plantilla_se_reactiva(self, mock_ws_delay):
        # Primer intento: plantilla inactiva -- no debe quemar el dedupe.
        template = NotificationTemplate.objects.create(
            slug='reactivable', name='x', is_active=False,
            ws_event_type='X', email_body='', subject='',
        )
        sent1 = NotificationCommands.dispatch_notification_once(
            user=self.user, template_slug='reactivable', context={}, dedupe_key='entidad:2',
        )
        self.assertFalse(sent1)

        # Se reactiva la plantilla -- la siguiente corrida del scanner SI debe notificar.
        template.is_active = True
        template.save(update_fields=['is_active'])
        sent2 = NotificationCommands.dispatch_notification_once(
            user=self.user, template_slug='reactivable', context={}, dedupe_key='entidad:2',
        )
        self.assertTrue(sent2)
        mock_ws_delay.assert_called_once()

    def test_marcador_de_dedupe_bloquea_reintento_una_vez_creado(self):
        NotificationTemplate.objects.create(
            slug='activa', name='x', is_active=True,
            ws_event_type='', email_body='', subject='',
        )
        sent1 = NotificationCommands.dispatch_notification_once(
            user=self.user, template_slug='activa', context={}, dedupe_key='entidad:3',
        )
        sent2 = NotificationCommands.dispatch_notification_once(
            user=self.user, template_slug='activa', context={}, dedupe_key='entidad:3',
        )
        self.assertTrue(sent1)
        self.assertFalse(sent2)


class AiProactiveRoomMessageStaffVisibilityTestCase(TransactionTestCase):
    """
    Fase 9 (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-01): antes
    ai_proactive_room_message_task (usada por notify_unattended_escalated_tickets, entre
    otros) solo difundia al cliente -- un ticket escalado a un agente humano y sin
    seguimiento nunca alertaba a NINGUN canal del staff. Ahora tambien llega a support_admins.
    """

    def setUp(self):
        self.user = User.objects.create_user(email='staff_visibility@test.sintel', password='x')

    @patch('channels.layers.get_channel_layer')
    def test_difunde_tanto_al_cliente_como_a_support_admins(self, mock_get_layer):
        from unittest.mock import AsyncMock
        from notifications.tasks import ai_proactive_room_message_task

        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_get_layer.return_value = mock_layer

        ai_proactive_room_message_task(
            user_id=self.user.id,
            template_slug='ticket_soporte_sin_seguimiento',
            context={'room_uuid': 'abc-123'},
        )

        groups_notified = {call.args[0] for call in mock_layer.group_send.call_args_list}
        self.assertIn(f'chat_{self.user.uuid}', groups_notified)
        self.assertIn('support_admins', groups_notified)


class AiProactiveRoomMessageRespectsPreferencesTestCase(TransactionTestCase):
    """
    Repaso de backlog (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-03): a
    diferencia de los demas canales de dispatch_notification, este mensaje se creaba/difundia
    incondicionalmente, ignorando UserNotificationPreference.
    """

    def setUp(self):
        self.user = User.objects.create_user(email='ai_proactive_prefs@test.sintel', password='x')

    def test_no_crea_mensaje_si_el_usuario_desactivo_web_socket(self):
        from support.models import ChatRoom, ChatMessage
        from notifications.tasks import ai_proactive_room_message_task

        UserNotificationPreference.objects.create(
            user=self.user, channel=CHANNEL_WEB_SOCKET, is_enabled=False,
        )
        UserNotificationPreference.objects.create(
            user=self.user, channel=CHANNEL_EMAIL, is_enabled=True,
        )

        ai_proactive_room_message_task(
            user_id=self.user.id, template_slug='ticket_soporte_sin_seguimiento',
            context={'room_uuid': 'abc-123'},
        )

        self.assertFalse(ChatRoom.objects.filter(user=self.user).exists())
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_crea_mensaje_si_no_hay_preferencias_registradas(self):
        from support.models import ChatMessage
        from notifications.tasks import ai_proactive_room_message_task

        ai_proactive_room_message_task(
            user_id=self.user.id, template_slug='ticket_soporte_sin_seguimiento',
            context={'room_uuid': 'abc-123'},
        )

        self.assertEqual(ChatMessage.objects.count(), 1)

    def test_crea_mensaje_si_web_socket_esta_explicitamente_habilitado(self):
        from support.models import ChatMessage
        from notifications.tasks import ai_proactive_room_message_task

        UserNotificationPreference.objects.create(
            user=self.user, channel=CHANNEL_WEB_SOCKET, is_enabled=True,
        )

        ai_proactive_room_message_task(
            user_id=self.user.id, template_slug='ticket_soporte_sin_seguimiento',
            context={'room_uuid': 'abc-123'},
        )

        self.assertEqual(ChatMessage.objects.count(), 1)


class SendWhatsappAgentReplyTaskTestCase(TransactionTestCase):
    """
    Fase 16 (AUDITORIA/30_AUDITORIA_PRUEBAS_E2E.md, 2026-08-03): antes, cuando un ticket de
    soporte escalaba a un humano y el agente respondia desde el panel, esa respuesta SOLO se
    difundia por WebSocket -- un cliente que hablaba unicamente por WhatsApp nunca la recibia.
    Este task es el bridge de vuelta hacia WhatsApp.
    """

    def setUp(self):
        self.user = User.objects.create_user(email='agent_reply_wa@test.sintel', password='x')

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    def test_reenvia_por_whatsapp_si_el_usuario_tiene_telefono_valido(self, mock_send_text):
        from accounts.models import UserProfile
        from notifications.tasks import send_whatsapp_agent_reply_task

        UserProfile.objects.create(user=self.user, phone_number='3001234567')

        send_whatsapp_agent_reply_task(user_id=self.user.id, text='Ya revisamos tu caso.')

        mock_send_text.assert_called_once_with('573001234567', 'Ya revisamos tu caso.')

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    def test_no_reenvia_si_el_usuario_no_tiene_telefono(self, mock_send_text):
        from notifications.tasks import send_whatsapp_agent_reply_task

        send_whatsapp_agent_reply_task(user_id=self.user.id, text='Ya revisamos tu caso.')

        mock_send_text.assert_not_called()

    @patch('notifications.clients.whatsapp.WhatsAppClient.send_text')
    def test_fallo_de_meta_no_propaga_excepcion(self, mock_send_text):
        # Ventana de 24h cerrada u otro rechazo de Meta -- no debe tumbar la tarea.
        from accounts.models import UserProfile
        from notifications.clients.whatsapp import WhatsAppApiError
        from notifications.tasks import send_whatsapp_agent_reply_task

        UserProfile.objects.create(user=self.user, phone_number='3001234567')
        mock_send_text.side_effect = WhatsAppApiError('Meta API respondio 400: ventana cerrada')

        send_whatsapp_agent_reply_task(user_id=self.user.id, text='Ya revisamos tu caso.')  # no debe lanzar

        mock_send_text.assert_called_once()
