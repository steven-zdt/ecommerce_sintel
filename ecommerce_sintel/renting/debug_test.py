from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from renting.models import RentingCategory, Equipment, EquipmentVariant, EquipmentImage

User = get_user_model()

_PNG_BYTES = bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000001000000010802000000'
    '907753de0000000c4944415478da6360000002000155a5ee0e000000004'
    '9454e44ae426082'
)

class DebugTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass123')
        self.category = RentingCategory.objects.create(name='Test Category', slug='test-category')
        self.equipment = Equipment.objects.create(
            category=self.category, name='API Test Equipment', slug='api-test-equipment',
            is_active=True, vendor=self.user,
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment, sku='API-001', rental_price_per_day=Decimal('100000.00'), stock=10,
        )
        EquipmentImage.objects.create(
            equipment=self.equipment,
            image=SimpleUploadedFile('api-test.png', _PNG_BYTES, content_type='image/png'),
            alt_text='API test image', image_type='PRINCIPAL', position=1,
        )

    def test_debug_hero(self):
        url = f'/renting/equipment/{self.equipment.uuid}/detail/'
        response = self.client.get(url)
        print("STATUS:", response.status_code)
        print(response.content[:3000])

    def test_debug_404(self):
        url = '/renting/equipment/00000000-0000-0000-0000-000000000000/detail/'
        response = self.client.get(url)
        print("STATUS 404case:", response.status_code)
        print(response.content[:1000])
