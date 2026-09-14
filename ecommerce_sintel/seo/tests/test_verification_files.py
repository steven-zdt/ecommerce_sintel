from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from rest_framework.test import APIClient

from seo.models import SeoMetaTagAuditLog, SiteVerificationFile
from seo.services.commands import VerificationFileCommands
from seo.services.selectors import VerificationFileSelector

User = get_user_model()

SEED_FILENAME = '0c6qg0sg1qsfxhoth3srzf53i62neb-meta.html'
SEED_CONTENT = '0c6qg0sg1qsfxhoth3srzf53i62neb'


class SeedVerificationFileTestCase(TestCase):
    def test_meta_verification_file_seeded(self):
        record = SiteVerificationFile.objects.get(filename=SEED_FILENAME)
        self.assertEqual(record.content, SEED_CONTENT)
        self.assertTrue(record.is_active)
        self.assertEqual(record.provider, 'meta')


class ServeVerificationFileViewTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_seeded_file_served_at_root_with_exact_content(self):
        response = Client().get(f'/{SEED_FILENAME}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), SEED_CONTENT)
        self.assertIn('text/html', response['Content-Type'])

    def test_unknown_filename_returns_404(self):
        response = Client().get('/does-not-exist.html')
        self.assertEqual(response.status_code, 404)

    def test_inactive_file_returns_404(self):
        record = SiteVerificationFile.objects.get(filename=SEED_FILENAME)
        VerificationFileCommands.toggle_active(record)  # -> inactive
        try:
            response = Client().get(f'/{SEED_FILENAME}')
            self.assertEqual(response.status_code, 404)
        finally:
            record.refresh_from_db()
            VerificationFileCommands.toggle_active(record)  # restore active

    def test_spa_routes_unaffected(self):
        response = Client().get('/tienda')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<div id="shop-spa-root">', response.content)


class VerificationFileModelTestCase(TestCase):
    def test_filename_validator_rejects_invalid_characters(self):
        record = SiteVerificationFile(
            name='Invalido', provider='custom', filename='../evil.html', content='x',
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_filename_validator_requires_html_extension(self):
        record = SiteVerificationFile(
            name='Invalido', provider='custom', filename='not-html.txt', content='x',
        )
        with self.assertRaises(ValidationError):
            record.full_clean()


class VerificationFileCommandsTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_create_writes_audit_log(self):
        record = VerificationFileCommands.create({
            'name': 'GSC verification', 'provider': 'google_search_console',
            'filename': 'gsc-verify-key.html', 'content': 'google-site-verification-code',
        })
        entry = SeoMetaTagAuditLog.objects.filter(
            meta_tag_name=f'[verification_file] {record.filename}',
            action=SeoMetaTagAuditLog.ACTION_CREATED,
        ).first()
        self.assertIsNotNone(entry)

    def test_delete_is_soft_and_excluded_from_render(self):
        record = VerificationFileCommands.create({
            'name': 'Temp', 'provider': 'custom', 'filename': 'temp-verify.html', 'content': 'x',
        })
        VerificationFileCommands.delete(record)
        record.refresh_from_db()
        self.assertTrue(record.is_deleted)
        self.assertIsNone(VerificationFileSelector.get_active_content_by_filename('temp-verify.html'))


class AdminVerificationFileApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email='vf_admin@example.com', password='Test12345!')
        self.regular = User.objects.create_user(email='vf_regular@example.com', password='Test12345!')
        self.base_url = '/api/v1/dashboard/seo/verification-files/'

    def test_anonymous_gets_401(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 401)

    def test_non_admin_gets_403(self):
        self.client.force_authenticate(user=self.regular)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_admin_full_lifecycle(self):
        self.client.force_authenticate(user=self.admin)

        create_resp = self.client.post(self.base_url, {
            'name': 'Bing verification', 'provider': 'bing',
            'filename': 'bing-verify-key.html', 'content': 'bing-code-123',
        }, format='json')
        self.assertEqual(create_resp.status_code, 201, create_resp.data)
        file_uuid = create_resp.data['uuid']
        self.assertEqual(create_resp.data['url_path'], '/bing-verify-key.html')

        served = Client().get('/bing-verify-key.html')
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.content.decode('utf-8'), 'bing-code-123')

        toggle_resp = self.client.post(f'{self.base_url}{file_uuid}/toggle/')
        self.assertEqual(toggle_resp.status_code, 200)
        self.assertFalse(toggle_resp.data['is_active'])

        served_after_toggle = Client().get('/bing-verify-key.html')
        self.assertEqual(served_after_toggle.status_code, 404)

        delete_resp = self.client.delete(f'{self.base_url}{file_uuid}/')
        self.assertEqual(delete_resp.status_code, 204)

    def test_reject_invalid_filename(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.base_url, {
            'name': 'Malicioso', 'provider': 'custom',
            'filename': '../../etc/passwd.html', 'content': 'x',
        }, format='json')
        self.assertEqual(response.status_code, 400)
