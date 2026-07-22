from django.test import TestCase

from organization.models import Company, ContactInfo, SocialLink
from organization.services.selectors import OrganizationSelector
from organization.services.commands import OrganizationCommands


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
