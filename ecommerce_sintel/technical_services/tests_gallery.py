"""
technical_services/tests_gallery.py

Plan "Rediseno ServiceForm + Content/Media" (2026-08-14) FASE 4/5 -- galeria
descriptiva de ServiceImage (caption/description/display_order) + comandos y
endpoints admin nuevos (update_image, replace_image, reorder_images).
Archivo separado, mismo criterio que tests_order_pricing.py/tests_packages.py
-- dominio propio, no mezclar con tests.py.
"""
import base64
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import UserProfile
from technical_services.models import ServiceCategory, ServiceImage, ServiceVariant, TechnicalService
from technical_services.services.commands import ServiceImageCommands

User = get_user_model()

# GIF 1x1 transparente valido -- Django ImageField exige contenido de imagen
# real (valida con PIL), no basta con bytes arbitrarios.
_GIF_1PX = base64.b64decode(
    'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBTAA7'
)


def _fake_image(name='foto.gif'):
    return SimpleUploadedFile(name, _GIF_1PX, content_type='image/gif')


class ServiceImageCommandsTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='gallery_cmd_admin@example.com', password='x')
        self.category = ServiceCategory.objects.create(name='Cat Gallery', slug='cat-gallery')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name='Servicio Galeria', slug='servicio-galeria',
        )

    def test_add_image_assigns_incremental_display_order(self):
        img1 = ServiceImageCommands.add_image(self.service, _fake_image('a.gif'))
        img2 = ServiceImageCommands.add_image(self.service, _fake_image('b.gif'))
        img3 = ServiceImageCommands.add_image(self.service, _fake_image('c.gif'))
        self.assertEqual(img1.display_order, 0)
        self.assertEqual(img2.display_order, 1)
        self.assertEqual(img3.display_order, 2)

    def test_add_image_stores_caption_and_description(self):
        img = ServiceImageCommands.add_image(
            self.service, _fake_image(), caption='Instalacion terminada', description='Vista general del panel.',
        )
        self.assertEqual(img.caption, 'Instalacion terminada')
        self.assertEqual(img.description, 'Vista general del panel.')

    def test_update_metadata_updates_only_allowed_fields(self):
        img = ServiceImageCommands.add_image(self.service, _fake_image())
        original_image_name = img.image.name
        updated = ServiceImageCommands.update_metadata(
            img, caption='Nuevo pie', description='Nueva descripcion', alt_text='nuevo alt',
        )
        updated.refresh_from_db()
        self.assertEqual(updated.caption, 'Nuevo pie')
        self.assertEqual(updated.description, 'Nueva descripcion')
        self.assertEqual(updated.alt_text, 'nuevo alt')
        self.assertEqual(updated.image.name, original_image_name)

    def test_replace_file_keeps_metadata_and_swaps_image(self):
        img = ServiceImageCommands.add_image(self.service, _fake_image('original.gif'), caption='Se queda igual')
        original_name = img.image.name
        updated = ServiceImageCommands.replace_file(img, _fake_image('reemplazo.gif'))
        updated.refresh_from_db()
        self.assertNotEqual(updated.image.name, original_name)
        self.assertEqual(updated.caption, 'Se queda igual')

    def test_reorder_persists_new_display_order(self):
        img1 = ServiceImageCommands.add_image(self.service, _fake_image('a.gif'))
        img2 = ServiceImageCommands.add_image(self.service, _fake_image('b.gif'))
        img3 = ServiceImageCommands.add_image(self.service, _fake_image('c.gif'))

        ServiceImageCommands.reorder(self.service, [str(img3.uuid), str(img1.uuid), str(img2.uuid)])

        img1.refresh_from_db(); img2.refresh_from_db(); img3.refresh_from_db()
        self.assertEqual(img3.display_order, 0)
        self.assertEqual(img1.display_order, 1)
        self.assertEqual(img2.display_order, 2)

        # Meta.ordering = ['display_order', ...] -- el queryset por defecto
        # ya refleja el nuevo orden sin pedir order_by() explicito.
        ordered = list(self.service.images.all())
        self.assertEqual([i.uuid for i in ordered], [img3.uuid, img1.uuid, img2.uuid])


class ServiceGalleryAdminAPITestCase(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='gallery_api_customer@example.com', password='x')
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.admin = User.objects.create_superuser(email='gallery_api_admin@example.com', password='x')

        self.category = ServiceCategory.objects.create(name='Cat Gallery API', slug='cat-gallery-api')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name='Servicio Galeria API', slug='servicio-galeria-api',
        )
        self.image = ServiceImageCommands.add_image(self.service, _fake_image(), caption='Original')

    def _url(self, action, image_uuid=None):
        base = f'/api/v1/dashboard/services/{self.service.uuid}/{action}/'
        return f'{base[:-1]}/{image_uuid}/' if image_uuid else base

    def test_add_image_accepts_caption_and_description(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            f'/api/v1/dashboard/services/{self.service.uuid}/add_image/',
            {'image': _fake_image('nueva.gif'), 'caption': 'Pie nuevo', 'description': 'Descripcion nueva'},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['caption'], 'Pie nuevo')
        self.assertEqual(resp.data['description'], 'Descripcion nueva')
        self.assertEqual(resp.data['display_order'], 1)  # la del setUp ya ocupa 0

    def test_update_image_requires_admin(self):
        url = f'/api/v1/dashboard/services/{self.service.uuid}/update_image/{self.image.uuid}/'
        resp = self.client.patch(url, {'caption': 'x'}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.client.force_authenticate(user=self.customer)
        resp = self.client.patch(url, {'caption': 'x'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_update_image_success(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/dashboard/services/{self.service.uuid}/update_image/{self.image.uuid}/'
        resp = self.client.patch(url, {'caption': 'Actualizado', 'description': 'Nueva desc'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['caption'], 'Actualizado')
        self.assertEqual(resp.data['description'], 'Nueva desc')
        self.image.refresh_from_db()
        self.assertEqual(self.image.caption, 'Actualizado')

    def test_replace_image_success(self):
        self.client.force_authenticate(user=self.admin)
        original_name = self.image.image.name
        url = f'/api/v1/dashboard/services/{self.service.uuid}/replace_image/{self.image.uuid}/'
        resp = self.client.post(url, {'image': _fake_image('reemplazo.gif')}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        self.image.refresh_from_db()
        self.assertNotEqual(self.image.image.name, original_name)
        self.assertEqual(self.image.caption, 'Original')  # metadata no se toco

    def test_replace_image_requires_file(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/dashboard/services/{self.service.uuid}/replace_image/{self.image.uuid}/'
        resp = self.client.post(url, {}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_reorder_images_success(self):
        img2 = ServiceImageCommands.add_image(self.service, _fake_image('b.gif'))
        img3 = ServiceImageCommands.add_image(self.service, _fake_image('c.gif'))

        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/dashboard/services/{self.service.uuid}/reorder_images/'
        resp = self.client.post(url, {
            'ordered_uuids': [str(img3.uuid), str(self.image.uuid), str(img2.uuid)],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        returned_order = [item['uuid'] for item in resp.data]
        self.assertEqual(returned_order, [str(img3.uuid), str(self.image.uuid), str(img2.uuid)])

    def test_reorder_images_requires_admin(self):
        url = f'/api/v1/dashboard/services/{self.service.uuid}/reorder_images/'
        resp = self.client.post(url, {'ordered_uuids': [str(self.image.uuid)]}, format='json')
        self.assertEqual(resp.status_code, 401)
