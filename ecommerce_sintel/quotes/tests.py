"""
Tests de regresion para Q-01 y Q-02 (auditoria enterprise, 2026-07-24).

Q-01: download_pdf era AllowAny + query directo por uuid (Quotation.objects.get),
      exponiendo PII (nombre, documento, telefono, direccion, GPS) y precios de
      CUALQUIER cotizacion a quien tuviera el enlace, sin sesion.
Q-02: add_attachment guardaba archivos sin limite de tamano, whitelist de
      extension ni verificacion de magic-bytes.

Ambos ya estan corregidos en quotes/api/views.py -- estos tests documentan el
comportamiento esperado y evitan que la correccion se pierda en un refactor.
"""
import datetime
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from quotes.models import Quotation

User = get_user_model()


def _make_quotation(user=None, **overrides):
    defaults = {
        'client_name': 'Cliente de Prueba',
        'client_email': 'cliente@example.com',
        'valid_until': datetime.date.today() + datetime.timedelta(days=30),
        'user': user,
    }
    defaults.update(overrides)
    return Quotation.objects.create(**defaults)


class QuotationDownloadPdfPermissionTestCase(APITestCase):
    """Q-01: el PDF solo debe ser accesible por el dueno (o staff)."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner_q01@example.com', password='testpassword123')
        self.other_user = User.objects.create_user(email='other_q01@example.com', password='testpassword123')
        self.quotation = _make_quotation(user=self.owner)
        self.url = f'/api/v1/quotes/quotations/{self.quotation.uuid}/download_pdf/'

    def test_anonymous_request_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_authenticated_user_cannot_download_it(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.url)
        # get_object() -> get_queryset() filtra por user: para alguien que no
        # es el dueno, la fila no existe en su queryset -> 404, nunca 200.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_download_it(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_staff_can_download_any_quotation(self):
        staff = User.objects.create_user(email='staff_q01@example.com', password='testpassword123', is_staff=True)
        self.client.force_authenticate(user=staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class QuotationAttachmentValidationTestCase(APITestCase):
    """Q-02: add_attachment debe validar tamano, extension y magic-bytes."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner_q02@example.com', password='testpassword123')
        self.quotation = _make_quotation(user=self.owner)
        self.url = f'/api/v1/quotes/quotations/{self.quotation.uuid}/add_attachment/'
        self.client.force_authenticate(user=self.owner)

    def test_rejects_executable_disguised_as_pdf(self):
        # Cabecera real de un ejecutable (MZ), extension declarada .pdf --
        # sin el chequeo de magic-bytes esto se guardaba tal cual.
        fake = SimpleUploadedFile('malware.pdf', b'MZ\x90\x00' + b'\x00' * 100, content_type='application/pdf')
        response = self.client.post(self.url, {'files': [fake]}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_file_over_size_limit(self):
        oversized = SimpleUploadedFile(
            'grande.pdf', b'%PDF' + b'\x00' * (21 * 1024 * 1024), content_type='application/pdf'
        )
        response = self.client.post(self.url, {'files': [oversized]}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_disallowed_extension(self):
        script = SimpleUploadedFile('script.exe', b'MZ\x90\x00', content_type='application/octet-stream')
        response = self.client.post(self.url, {'files': [script]}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accepts_legitimate_pdf(self):
        real_pdf = SimpleUploadedFile('cotizacion.pdf', b'%PDF-1.4\n%mock pdf content', content_type='application/pdf')
        response = self.client.post(self.url, {'files': [real_pdf]}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['uploaded']), 1)
