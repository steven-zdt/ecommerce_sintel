from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from rest_framework.test import APIClient

from seo.models import SeoMetaTagAuditLog, SiteMetaTag
from seo.services.commands import MetaTagCommands
from seo.services.sanitizer import sanitize_meta_html
from seo.services.selectors import MetaTagSelector

User = get_user_model()

VERIFICATION_META_TAG = (
    '<meta name="facebook-domain-verification" content="0c6qg0sg1qsfxhoth3srzf53i62neb">'
)


class SeedDataTestCase(TestCase):
    """La migracion 0002 debe sembrar el registro sin que el codigo tenga el
    valor hardcodeado en ningun template/settings."""

    def test_meta_business_verification_seeded(self):
        tag = SiteMetaTag.objects.get(
            provider=SiteMetaTag.PROVIDER_META,
            meta_name='facebook-domain-verification',
        )
        self.assertEqual(tag.meta_content, '0c6qg0sg1qsfxhoth3srzf53i62neb')
        self.assertTrue(tag.is_active)
        self.assertEqual(tag.environment, SiteMetaTag.ENV_ALL)


class HeadRenderTestCase(TestCase):
    """Requisito central del enunciado: el HTML inicial del servidor debe
    traer la metaetiqueta dentro de <head>, una unica vez, sin JS."""

    def setUp(self):
        cache.clear()

    def test_meta_tag_rendered_once_inside_head_not_in_body(self):
        response = Client().get('/')
        html = response.content.decode('utf-8')

        self.assertEqual(html.count(VERIFICATION_META_TAG), 1)

        head_start = html.index('<head')
        head_end = html.index('</head>')
        body_start = html.index('<body')
        needle_index = html.index(VERIFICATION_META_TAG)

        self.assertTrue(head_start < needle_index < head_end)
        self.assertTrue(needle_index < body_start)


class MetaTagSelectorRenderFilterTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def _active_html(self, path='/', environment=SiteMetaTag.ENV_PRODUCTION):
        return MetaTagSelector.list_active_for_render(path=path, environment=environment)

    def test_inactive_tag_excluded(self):
        SiteMetaTag.objects.create(
            name='GTM inactivo', provider=SiteMetaTag.PROVIDER_GOOGLE_TAG_MANAGER,
            tag_type=SiteMetaTag.TYPE_ANALYTICS,
            meta_name='gtm-inactive-key', meta_content='GTM-XXXX', is_active=False,
        )
        self.assertFalse(any('gtm-inactive-key' in h for h in self._active_html()))

    def test_wrong_environment_excluded(self):
        SiteMetaTag.objects.create(
            name='Solo dev', provider=SiteMetaTag.PROVIDER_CUSTOM, tag_type=SiteMetaTag.TYPE_CUSTOM,
            meta_name='dev-only-key', meta_content='x', is_active=True,
            environment=SiteMetaTag.ENV_DEVELOPMENT,
        )
        self.assertFalse(any('dev-only-key' in h for h in self._active_html(environment=SiteMetaTag.ENV_PRODUCTION)))
        self.assertTrue(any('dev-only-key' in h for h in self._active_html(environment=SiteMetaTag.ENV_DEVELOPMENT)))

    def test_target_page_filter(self):
        SiteMetaTag.objects.create(
            name='Solo tienda', provider=SiteMetaTag.PROVIDER_CUSTOM, tag_type=SiteMetaTag.TYPE_CUSTOM,
            meta_name='shop-only-key', meta_content='x', is_active=True, target_page='/tienda',
        )
        self.assertFalse(any('shop-only-key' in h for h in self._active_html(path='/')))
        self.assertTrue(any('shop-only-key' in h for h in self._active_html(path='/tienda/producto/x')))

    def test_soft_deleted_excluded(self):
        tag = SiteMetaTag.objects.create(
            name='Borrado', provider=SiteMetaTag.PROVIDER_CUSTOM, tag_type=SiteMetaTag.TYPE_CUSTOM,
            meta_name='deleted-key', meta_content='x', is_active=True,
        )
        tag.is_deleted = True
        tag.save(update_fields=['is_deleted'])
        self.assertFalse(any('deleted-key' in h for h in self._active_html()))


class SanitizerTestCase(TestCase):
    def test_rejects_script_tag(self):
        with self.assertRaises(ValidationError):
            sanitize_meta_html('<script>alert(1)</script>')

    def test_rejects_event_handler_attribute(self):
        with self.assertRaises(ValidationError):
            sanitize_meta_html('<meta name="x" content="y" onerror="alert(1)">')

    def test_rejects_javascript_uri_in_value(self):
        with self.assertRaises(ValidationError):
            sanitize_meta_html('<meta http-equiv="refresh" content="0;url=javascript:alert(1)">')

    def test_rejects_text_outside_meta_tags(self):
        with self.assertRaises(ValidationError):
            sanitize_meta_html('<meta name="x" content="y">algo de texto suelto')

    def test_accepts_valid_meta_and_drops_unknown_attrs(self):
        result = sanitize_meta_html('<meta name="foo" content="bar" data-track="1">')
        self.assertIn('name="foo"', result)
        self.assertIn('content="bar"', result)
        self.assertNotIn('data-track', result)

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(sanitize_meta_html(''), '')
        self.assertEqual(sanitize_meta_html('   '), '')


class MetaTagCommandsTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def _base_data(self, **overrides):
        data = dict(
            name='Tag de prueba', provider=SiteMetaTag.PROVIDER_CUSTOM, tag_type=SiteMetaTag.TYPE_CUSTOM,
            description='', meta_name='dup-key', meta_content='1', html_snippet='',
            priority=0, is_active=True, target_page='', environment=SiteMetaTag.ENV_ALL,
        )
        data.update(overrides)
        return data

    def test_duplicate_active_provider_meta_name_rejected(self):
        MetaTagCommands.create(self._base_data())
        with self.assertRaises(ValidationError):
            MetaTagCommands.create(self._base_data(name='Otro nombre'))

    def test_create_writes_audit_log_with_action_created(self):
        tag = MetaTagCommands.create(self._base_data(meta_name='audit-key'))
        entry = SeoMetaTagAuditLog.objects.filter(
            meta_tag=tag, action=SeoMetaTagAuditLog.ACTION_CREATED,
        ).first()
        self.assertIsNotNone(entry)

    def test_update_writes_audit_log_with_action_updated(self):
        tag = MetaTagCommands.create(self._base_data(meta_name='update-key'))
        MetaTagCommands.update(tag, {'description': 'nueva descripcion'})
        self.assertTrue(
            SeoMetaTagAuditLog.objects.filter(meta_tag=tag, action=SeoMetaTagAuditLog.ACTION_UPDATED).exists()
        )

    def test_delete_is_soft_and_logs(self):
        tag = MetaTagCommands.create(self._base_data(meta_name='delete-key'))
        MetaTagCommands.delete(tag)
        tag.refresh_from_db()
        self.assertTrue(tag.is_deleted)
        self.assertFalse(tag.is_active)
        self.assertTrue(
            SeoMetaTagAuditLog.objects.filter(meta_tag=tag, action=SeoMetaTagAuditLog.ACTION_DELETED).exists()
        )

    def test_duplicate_creates_inactive_copy(self):
        tag = MetaTagCommands.create(self._base_data(meta_name='dupe-src-key'))
        copy = MetaTagCommands.duplicate(tag)
        self.assertFalse(copy.is_active)
        self.assertNotEqual(copy.uuid, tag.uuid)
        self.assertEqual(copy.meta_name, tag.meta_name)

    def test_toggle_active_updates_render_cache(self):
        tag = MetaTagCommands.create(self._base_data(meta_name='toggle-key'))
        html_before = MetaTagSelector.list_active_for_render(environment=SiteMetaTag.ENV_ALL)
        self.assertTrue(any('toggle-key' in h for h in html_before))

        MetaTagCommands.toggle_active(tag)  # -> inactive
        html_after_off = MetaTagSelector.list_active_for_render(environment=SiteMetaTag.ENV_ALL)
        self.assertFalse(any('toggle-key' in h for h in html_after_off))

        tag.refresh_from_db()
        MetaTagCommands.toggle_active(tag)  # -> active again
        html_after_on = MetaTagSelector.list_active_for_render(environment=SiteMetaTag.ENV_ALL)
        self.assertTrue(any('toggle-key' in h for h in html_after_on))

    def test_model_clean_requires_meta_pair_or_snippet(self):
        tag = SiteMetaTag(
            name='Invalido', provider=SiteMetaTag.PROVIDER_CUSTOM, tag_type=SiteMetaTag.TYPE_CUSTOM,
        )
        with self.assertRaises(ValidationError):
            tag.full_clean()


class AdminSeoMetaTagApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email='seo_admin@example.com', password='Test12345!')
        self.regular = User.objects.create_user(email='seo_regular@example.com', password='Test12345!')
        self.base_url = '/api/v1/dashboard/seo/meta-tags/'

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
            'name': 'Google Analytics', 'provider': 'google_analytics', 'tag_type': 'analytics',
            'meta_name': 'ga-lifecycle-key', 'meta_content': 'G-XXXX',
        }, format='json')
        self.assertEqual(create_resp.status_code, 201, create_resp.data)
        tag_uuid = create_resp.data['uuid']

        preview_resp = self.client.get(f'{self.base_url}{tag_uuid}/preview/')
        self.assertEqual(preview_resp.status_code, 200)
        self.assertIn('ga-lifecycle-key', preview_resp.data['html'])

        duplicate_resp = self.client.post(f'{self.base_url}{tag_uuid}/duplicate/')
        self.assertEqual(duplicate_resp.status_code, 201)
        self.assertFalse(duplicate_resp.data['is_active'])

        history_resp = self.client.get(f'{self.base_url}{tag_uuid}/history/')
        self.assertEqual(history_resp.status_code, 200)
        self.assertGreaterEqual(len(history_resp.data), 1)

        toggle_resp = self.client.post(f'{self.base_url}{tag_uuid}/toggle/')
        self.assertEqual(toggle_resp.status_code, 200)
        self.assertFalse(toggle_resp.data['is_active'])

        export_resp = self.client.get(f'{self.base_url}export/')
        self.assertEqual(export_resp.status_code, 200)
        self.assertTrue(any(item['meta_name'] == 'ga-lifecycle-key' for item in export_resp.data['items']))

        delete_resp = self.client.delete(f'{self.base_url}{tag_uuid}/')
        self.assertEqual(delete_resp.status_code, 204)

    def test_reject_script_via_html_snippet(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.base_url, {
            'name': 'Malicioso', 'provider': 'custom', 'tag_type': 'custom',
            'html_snippet': '<script>alert(1)</script>',
        }, format='json')
        self.assertEqual(response.status_code, 400)
