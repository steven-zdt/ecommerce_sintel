from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from django.test import TestCase
from users.models import User
from renting.models import RentingBrand, RentingCategory


class RentingUuidDeleteVerifyTest(TestCase):
    def test_delete_brand_and_category_by_uuid(self):
        admin = User.objects.create_user(
            email='uuid_fix_admin_verify@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)

        brand = RentingBrand.objects.create(name='TempBrand', slug='temp-brand-uuid-test')
        cat = RentingCategory.objects.create(name='TempCat', slug='temp-cat-uuid-test')

        # Old buggy call (delete by integer id) raises ValidationError -> reproduces the reported 500
        try:
            client.delete(f'/api/v1/dashboard/renting-brands/{brand.id}/')
            self.fail('expected ValidationError for id-based delete (bug should reproduce)')
        except ValidationError as e:
            print('Reproduced bug on brand id-delete:', e)

        # Fixed call (delete by uuid) -> 204
        resp_good = client.delete(f'/api/v1/dashboard/renting-brands/{brand.uuid}/')
        print('DELETE brand by uuid status:', resp_good.status_code)
        self.assertEqual(resp_good.status_code, 204)

        try:
            client.delete(f'/api/v1/dashboard/renting-categories/{cat.id}/')
            self.fail('expected ValidationError for id-based delete (bug should reproduce)')
        except ValidationError as e:
            print('Reproduced bug on category id-delete:', e)

        resp_cat_good = client.delete(f'/api/v1/dashboard/renting-categories/{cat.uuid}/')
        print('DELETE category by uuid status:', resp_cat_good.status_code)
        self.assertEqual(resp_cat_good.status_code, 204)
