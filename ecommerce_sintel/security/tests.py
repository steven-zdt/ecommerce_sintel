from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from security.models import SecurityEvent
from security.services.commands import SecurityCommands

User = get_user_model()


class SecurityEventLoggingTestCase(TestCase):

    def test_log_event_creates_row(self):
        SecurityCommands.log_event(SecurityEvent.LOGIN_FAILED, severity=SecurityEvent.SEVERITY_WARNING,
                                    metadata={'email': 'x@example.com'})
        self.assertEqual(SecurityEvent.objects.filter(event_type=SecurityEvent.LOGIN_FAILED).count(), 1)

    def test_log_event_never_raises(self):
        # metadata no serializable -- no debe propagar la excepcion al caller
        class Unserializable:
            pass
        SecurityCommands.log_event(SecurityEvent.FILE_REJECTED, metadata={'bad': Unserializable()})


class SecurityHealthViewTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email='admin_sec@example.com', password='Test12345!')

    def test_health_requires_admin(self):
        response = self.client.get('/api/v1/security/health/')
        self.assertEqual(response.status_code, 401)

    def test_health_ok_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/security/health/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('db', response.data)
