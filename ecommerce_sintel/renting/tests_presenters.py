"""
Tests para EquipmentPublicDetailPresenter y EquipmentPricingPresenter.

Estos tests validan que los presenters generan DTOs correctamente
y que el endpoint /detail/ retorna la información esperada.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from renting.models import (
    RentingCategory, Equipment, EquipmentVariant,
    RentalFeature, RentalSpecificationGroup, RentalSpecification,
    RentalIncludedItem, RentalExcludedItem, RentalOptionalService,
    RentalFAQ, EquipmentImage, EquipmentReview,
)
from renting.services.presenters import (
    EquipmentPublicDetailPresenter, EquipmentPricingPresenter,
)

User = get_user_model()


class EquipmentPricingPresenterTestCase(TestCase):
    def setUp(self):
        self.category = RentingCategory.objects.create(
            name='Test Category', slug='test-category',
        )
        self.equipment = Equipment.objects.create(
            category=self.category,
            name='Test Equipment',
            slug='test-equipment',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment,
            sku='TEST-001',
            rental_price_per_day=Decimal('100000.00'),
            stock=10,
        )

    def test_pricing_presenter_basic_pricing(self):
        presenter = EquipmentPricingPresenter(
            self.variant,
            marketing_config={},
            cost_rules=[],
        )
        dto = presenter.present()

        assert dto.price_per_day == Decimal('100000.00')
        assert dto.formatted_price_per_day == '$100.000'
        assert dto.currency_code == 'COP'
        assert dto.currency_symbol == '$'

    def test_pricing_presenter_discount_calculation(self):
        presenter = EquipmentPricingPresenter(
            self.variant,
            marketing_config={
                'reference_price': Decimal('120000.00'),
                'promo_price': Decimal('100000.00'),
            },
            cost_rules=[],
        )
        dto = presenter.present()

        assert dto.has_promotion == True
        assert dto.discount_percentage == 16
        assert dto.discount_amount == Decimal('20000.00')
        assert dto.has_promotion == True

    def test_pricing_presenter_hourly_pricing(self):
        self.variant.rental_price_per_hour = Decimal('5000.00')
        self.variant.save()

        presenter = EquipmentPricingPresenter(
            self.variant,
            marketing_config={},
            cost_rules=[],
        )
        dto = presenter.present()

        assert dto.price_per_hour == Decimal('5000.00')
        assert dto.formatted_price_per_hour == '$5.000'


class EquipmentPublicDetailPresenterTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123',
        )
        self.category = RentingCategory.objects.create(
            name='Test Category', slug='test-category',
        )
        self.equipment = Equipment.objects.create(
            category=self.category,
            name='Premium Equipment',
            slug='premium-equipment',
            description='A premium test equipment',
            is_active=True,
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment,
            sku='PREM-001',
            rental_price_per_day=Decimal('150000.00'),
            stock=5,
        )
        EquipmentImage.objects.create(
            equipment=self.equipment,
            image_url='https://example.com/image1.jpg',
            alt_text='Main image',
            image_type='PRINCIPAL',
            order=1,
        )

    def test_detail_presenter_returns_complete_dto(self):
        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto is not None
        assert dto.uuid == str(self.equipment.uuid)
        assert dto.slug == self.equipment.slug

    def test_detail_presenter_hero_section(self):
        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.hero is not None
        assert dto.hero.name == 'Premium Equipment'
        assert dto.hero.cta_enabled == True
        assert dto.hero.hero_image is not None

    def test_detail_presenter_availability_available(self):
        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.availability is not None
        assert dto.availability.status == 'available'
        assert dto.availability.available_now == 5

    def test_detail_presenter_pricing(self):
        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.pricing is not None
        assert dto.pricing.price_per_day == Decimal('150000.00')

    def test_detail_presenter_features(self):
        RentalFeature.objects.create(
            equipment=self.equipment,
            title='Power',
            value='20 kW',
            is_active=True,
        )
        RentalFeature.objects.create(
            equipment=self.equipment,
            title='Weight',
            value='500 kg',
            is_active=False,
        )

        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.technical is not None
        assert len(dto.technical.features) == 1
        assert dto.technical.features[0].title == 'Power'

    def test_detail_presenter_included_items(self):
        RentalIncludedItem.objects.create(
            equipment=self.equipment,
            title='Transport',
            description='Included in rental',
        )

        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.services is not None
        assert len(dto.services.included_items) == 1
        assert dto.services.included_items[0].title == 'Transport'

    def test_detail_presenter_optional_services(self):
        service = RentalOptionalService.objects.create(
            equipment=self.equipment,
            title='Operator',
            description='Professional operator',
            price_per_hour=Decimal('25000.00'),
            is_active=True,
        )

        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.services is not None
        assert len(dto.services.optional_services) == 1
        assert dto.services.optional_services[0].title == 'Operator'
        assert '$25.000' in dto.services.optional_services[0].formatted_price

    def test_detail_presenter_faqs(self):
        RentalFAQ.objects.create(
            equipment=self.equipment,
            question='Is it available?',
            answer='Yes, always in stock.',
            is_active=True,
        )
        RentalFAQ.objects.create(
            equipment=self.equipment,
            question='Hidden question',
            answer='Hidden answer',
            is_active=False,
        )

        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert len(dto.faqs) == 1
        assert dto.faqs[0].question == 'Is it available?'

    def test_detail_presenter_reviews(self):
        EquipmentReview.objects.create(
            equipment=self.equipment,
            user=self.user,
            rating=5,
            comment='Excellent equipment!',
            is_active=True,
        )
        EquipmentReview.objects.create(
            equipment=self.equipment,
            user=self.user,
            rating=4,
            comment='Good quality',
            is_active=True,
        )

        presenter = EquipmentPublicDetailPresenter(self.equipment, user=self.user)
        dto = presenter.present()

        assert dto.reviews is not None
        assert dto.reviews.total_count == 2
        assert dto.reviews.average_rating == 4.5


class EquipmentDetailEndpointTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123',
        )
        self.category = RentingCategory.objects.create(
            name='Test Category', slug='test-category',
        )
        self.equipment = Equipment.objects.create(
            category=self.category,
            name='API Test Equipment',
            slug='api-test-equipment',
            is_active=True,
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment,
            sku='API-001',
            rental_price_per_day=Decimal('100000.00'),
            stock=10,
        )
        EquipmentImage.objects.create(
            equipment=self.equipment,
            image_url='https://example.com/api-test.jpg',
            alt_text='API test image',
            image_type='PRINCIPAL',
            order=1,
        )

    def test_detail_endpoint_returns_200(self):
        url = f'/renting/equipment/{self.equipment.uuid}/detail/'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_detail_endpoint_response_structure(self):
        url = f'/renting/equipment/{self.equipment.uuid}/detail/'
        response = self.client.get(url)

        data = response.json()
        assert 'uuid' in data
        assert 'slug' in data
        assert 'hero' in data
        assert 'pricing' in data
        assert 'marketing' in data
        assert 'technical' in data
        assert 'services' in data
        assert 'media' in data
        assert 'faqs' in data
        assert 'reviews' in data
        assert 'availability' in data
        assert 'commercial_options' in data
        assert 'logistics' in data
        assert 'related_equipment' in data
        assert 'seo' in data

    def test_detail_endpoint_hero_data(self):
        url = f'/renting/equipment/{self.equipment.uuid}/detail/'
        response = self.client.get(url)

        data = response.json()
        hero = data['hero']

        assert hero['name'] == 'API Test Equipment'
        assert hero['cta_enabled'] == True
        assert hero['hero_image'] is not None

    def test_detail_endpoint_pricing_data(self):
        url = f'/renting/equipment/{self.equipment.uuid}/detail/'
        response = self.client.get(url)

        data = response.json()
        pricing = data['pricing']

        assert pricing['price_per_day'] is not None
        assert pricing['formatted_price_per_day'] == '$100.000'
        assert pricing['currency_code'] == 'COP'

    def test_detail_endpoint_with_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        url = f'/renting/equipment/{self.equipment.uuid}/detail/'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['uuid'] == str(self.equipment.uuid)

    def test_detail_endpoint_404_on_nonexistent_equipment(self):
        url = f'/renting/equipment/00000000-0000-0000-0000-000000000000/detail/'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_endpoint_no_breaking_changes_to_list_endpoint(self):
        url = f'/renting/equipment/'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_detail_endpoint_no_breaking_changes_to_retrieve_endpoint(self):
        url = f'/renting/equipment/{self.equipment.uuid}/'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
