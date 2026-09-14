from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from organization.models import Company, ContactInfo, SocialLink, CommunicationEvent, EmailSettings
from organization.services.selectors import OrganizationSelector
from organization.services.commands import OrganizationCommands

User = get_user_model()


class SingletonModelsTests(TestCase):
    """
    Migrados desde core/tests/test_models_and_signals.py (2026-07-12) --
    Company/Branding reemplazan a core.SiteBrandConfig, ContactInfo reemplaza
    a core.CompanyContactInfo. Mismo patron singleton (SingletonMixin.save()).
    """

    def test_only_one_active_company(self):
        c1 = Company.objects.create(trade_name='Empresa 1', is_active=True)
        c2 = Company.objects.create(trade_name='Empresa 2', is_active=True)

        c1.refresh_from_db()
        c2.refresh_from_db()

        self.assertFalse(c1.is_active)
        self.assertTrue(c2.is_active)
        self.assertEqual(Company.objects.filter(is_active=True).count(), 1)

    def test_only_one_active_contact_info(self):
        contact1 = ContactInfo.objects.create(email='a@example.com', is_active=True)
        contact2 = ContactInfo.objects.create(email='b@example.com', is_active=True)

        contact1.refresh_from_db()
        contact2.refresh_from_db()

        self.assertFalse(contact1.is_active)
        self.assertTrue(contact2.is_active)
        self.assertEqual(ContactInfo.objects.filter(is_active=True).count(), 1)

    def test_social_link_is_not_a_singleton(self):
        """A diferencia de los demas modelos, puede haber muchos SocialLink activos."""
        SocialLink.objects.create(platform='Facebook', url='https://facebook.com/x')
        SocialLink.objects.create(platform='Instagram', url='https://instagram.com/x')

        self.assertEqual(SocialLink.objects.filter(is_active=True).count(), 2)

    def test_constraint_de_bd_bloquea_dos_filas_activas_simultaneas(self):
        """
        Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01): SingletonMixin.save()
        evita 2 filas activas en el caso secuencial (los 2 tests de arriba), pero no protegia
        contra 2 requests concurrentes que ambas ven "sin fila activa" y crean la suya -- el
        unique constraint parcial es la garantia real a nivel de BD. bulk_create() bypasea
        save() a proposito aqui, simulando exactamente esa condicion de carrera.
        """
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Company.objects.bulk_create([
                    Company(trade_name='Carrera A', is_active=True),
                    Company(trade_name='Carrera B', is_active=True),
                ])


class OrganizationSelectorAndCommandsTests(TestCase):

    def test_upsert_company_creates_then_updates(self):
        OrganizationCommands.upsert_company({'trade_name': 'Sintel'})
        company = OrganizationSelector.get_company()
        self.assertEqual(company.trade_name, 'Sintel')

        OrganizationCommands.upsert_company({'trade_name': 'Sintel Technology'})
        company.refresh_from_db()
        self.assertEqual(company.trade_name, 'Sintel Technology')
        self.assertEqual(Company.objects.count(), 1)

    def test_upsert_contact_info_creates_then_updates(self):
        OrganizationCommands.upsert_contact_info({'email': 'a@example.com'})
        contact = OrganizationSelector.get_contact_info()
        self.assertEqual(contact.email, 'a@example.com')

        OrganizationCommands.upsert_contact_info({'email': 'b@example.com'})
        contact.refresh_from_db()
        self.assertEqual(contact.email, 'b@example.com')
        self.assertEqual(ContactInfo.objects.count(), 1)

    def test_social_link_crud(self):
        link = OrganizationCommands.create_social_link(platform='Facebook', url='https://facebook.com/x')
        self.assertEqual(OrganizationSelector.list_social_links().count(), 1)

        OrganizationCommands.update_social_link(link, {'display_order': 5})
        link.refresh_from_db()
        self.assertEqual(link.display_order, 5)

        OrganizationCommands.delete_social_link(link)
        self.assertEqual(OrganizationSelector.list_social_links().count(), 0)

    def test_log_communication_event_anonymous_has_no_user(self):
        event = OrganizationCommands.log_communication_event(
            event_type=CommunicationEvent.EVENT_PANEL_OPEN, module='home',
        )
        self.assertIsNone(event.user)

    def test_log_communication_event_authenticated_keeps_user(self):
        user = User.objects.create_user(email='comm@example.com', password='pass12345')
        event = OrganizationCommands.log_communication_event(
            event_type=CommunicationEvent.EVENT_CHANNEL_CLICK, channel='whatsapp',
            module='shop', user=user, metadata={'product_name': 'Camara IP'},
        )
        self.assertEqual(event.user, user)
        self.assertEqual(event.metadata['product_name'], 'Camara IP')


class CommunicationEventEndpointTestCase(TestCase):
    """
    Centro de Comunicacion (2026-07-31) -- endpoint publico (AllowAny,
    visitantes anonimos incluidos), unico caso de escritura no-admin de
    esta app.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/organization/communication-events/'

    def test_anonymous_can_log_panel_open(self):
        response = self.client.post(
            self.url, {'event_type': 'panel_open', 'module': 'home'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CommunicationEvent.objects.count(), 1)
        self.assertIsNone(CommunicationEvent.objects.first().user)

    def test_authenticated_click_records_real_user(self):
        user = User.objects.create_user(email='comm2@example.com', password='pass12345')
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.url,
            {'event_type': 'channel_click', 'channel': 'whatsapp', 'module': 'renting',
             'metadata': {'page_path': '/alquiler/abc'}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = CommunicationEvent.objects.get()
        self.assertEqual(event.user, user)
        self.assertEqual(event.channel, 'whatsapp')
        self.assertEqual(event.metadata['page_path'], '/alquiler/abc')

    def test_invalid_event_type_is_rejected(self):
        response = self.client.post(self.url, {'event_type': 'not-a-real-type'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CommunicationEvent.objects.count(), 0)


class EmailSettingsCacheTestCase(TestCase):
    """Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01)."""

    def setUp(self):
        from django.core.cache import cache
        from organization.services.selectors import EMAIL_SETTINGS_CACHE_KEY
        cache.delete(EMAIL_SETTINGS_CACHE_KEY)

    def test_get_email_settings_se_cachea_y_se_invalida_al_actualizar(self):
        from django.core.cache import cache
        from organization.services.selectors import EMAIL_SETTINGS_CACHE_KEY

        OrganizationCommands.upsert_email_settings({'default_from_email': 'primero@sintel.net.co'})
        first = OrganizationSelector.get_email_settings()
        self.assertEqual(first.default_from_email, 'primero@sintel.net.co')

        # Cambio directo en BD, sin pasar por el ViewSet -- no invalida el cache.
        EmailSettings.objects.filter(pk=first.pk).update(default_from_email='directo-en-bd@sintel.net.co')
        still_cached = OrganizationSelector.get_email_settings()
        self.assertEqual(still_cached.default_from_email, 'primero@sintel.net.co')

        # Simula la invalidacion que hace EmailSettingsViewSet.update_settings().
        cache.delete(EMAIL_SETTINGS_CACHE_KEY)
        fresh = OrganizationSelector.get_email_settings()
        self.assertEqual(fresh.default_from_email, 'directo-en-bd@sintel.net.co')

    def test_endpoint_de_update_invalida_el_cache_automaticamente(self):
        admin = User.objects.create_user(
            email='admin_email_settings@example.com', password='pass12345',
            is_staff=True, is_superuser=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)

        OrganizationCommands.upsert_email_settings({'default_from_email': 'viejo@sintel.net.co'})
        OrganizationSelector.get_email_settings()  # fuerza el cache con el valor viejo

        response = client.post(
            '/api/v1/organization/email-settings/update/',
            {'default_from_email': 'nuevo@sintel.net.co'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OrganizationSelector.get_email_settings().default_from_email, 'nuevo@sintel.net.co')


class OrganizationInputValidationTestCase(TestCase):
    """Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01): email/telefono ahora se
    validan en el serializer, no se descubren rotos cuando el Communication Center los usa."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin_validation@example.com', password='pass12345',
            is_staff=True, is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_telefono_invalido_en_contacto_es_rechazado(self):
        response = self.client.post(
            '/api/v1/organization/contact/update/', {'phone': '12345'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_invalido_en_contacto_es_rechazado(self):
        response = self.client.post(
            '/api/v1/organization/contact/update/', {'email': 'no-es-un-email'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_telefono_colombiano_valido_es_aceptado(self):
        response = self.client.post(
            '/api/v1/organization/contact/update/', {'phone': '3001234567'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_telefono_con_indicativo_y_separadores_es_normalizado(self):
        response = self.client.post(
            '/api/v1/organization/contact/update/', {'phone': '+57 314 460 1878'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], '3144601878')

    def test_email_invalido_en_email_settings_es_rechazado(self):
        response = self.client.post(
            '/api/v1/organization/email-settings/update/',
            {'default_from_email': 'no-es-un-email'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
