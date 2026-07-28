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
    CHANNEL_EMAIL, CHANNEL_WHATSAPP, CHANNEL_WEB_SOCKET
)
from notifications.services.commands import NotificationCommands
from notifications.clients.whatsapp import (
    WhatsAppClient, WhatsAppApiError, WhatsAppAuthError, WhatsAppConfigError
)
from notifications.tasks import (
    send_ws_notification_task, send_email_notification_task, send_whatsapp_notification_task
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

    @override_settings(META_ACCESS_TOKEN='valid_token', WHATSAPP_PHONE_NUMBER_ID='valid_phone_id')
    @patch('requests.Session.post')
    def test_whatsapp_client_send_template_auth_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = '{"error": "Invalid OAuth Access Token"}'
        mock_post.return_value = mock_response

        client = WhatsAppClient()
        with self.assertRaises(WhatsAppAuthError):
            client.send_template(
                to="573001234567",
                template_name="test",
                variables={}
            )

    @override_settings(META_ACCESS_TOKEN='valid_token', WHATSAPP_PHONE_NUMBER_ID='valid_phone_id')
    @patch('requests.Session.post')
    def test_whatsapp_client_send_template_api_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = '{"error": "Internal Server Error"}'
        mock_post.return_value = mock_response

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
    @patch('requests.Session.post')
    def test_whatsapp_client_send_template_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.HBgLNTczMDA0NTY3ODkwFQIAERg"}]
        }
        mock_post.return_value = mock_response

        client = WhatsAppClient()
        msg_id = client.send_template(
            to="573001234567",
            template_name="test",
            variables={"var1": "val1"}
        )

        self.assertEqual(msg_id, "wamid.HBgLNTczMDA0NTY3ODkwFQIAERg")
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]['json']
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
