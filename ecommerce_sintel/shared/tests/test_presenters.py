"""
Tests para presenters de UnifiedPublicDetailDTO.

Verifica que cada presenter convierte correctamente el modelo a DTO.
"""

from django.test import TestCase


class RentingPublicDetailPresenterTestCase(TestCase):
    """Tests para RentingPublicDetailPresenter."""

    def test_presenter_imports(self):
        """Verifica que los presenters puedan importarse sin errores."""
        from shared.presenters import (
            PublicDetailPresenterBase,
            RentingPublicDetailPresenter,
            ShopPublicDetailPresenter,
            ServicePublicDetailPresenter,
        )
        self.assertIsNotNone(PublicDetailPresenterBase)
        self.assertIsNotNone(RentingPublicDetailPresenter)
        self.assertIsNotNone(ShopPublicDetailPresenter)
        self.assertIsNotNone(ServicePublicDetailPresenter)

    def test_dto_imports(self):
        """Verifica que los DTOs puedan importarse sin errores."""
        from shared.dtos import UnifiedPublicDetailDTO
        self.assertIsNotNone(UnifiedPublicDetailDTO)

    def test_serializer_imports(self):
        """Verifica que el serializer pueda importarse sin errores."""
        from shared.serializers import UnifiedPublicDetailDTOSerializer
        self.assertIsNotNone(UnifiedPublicDetailDTOSerializer)


class UnifiedPublicDetailDTOTestCase(TestCase):
    """Tests para UnifiedPublicDetailDTO."""

    def test_dto_creation(self):
        """Verifica que se puede crear un DTO básico."""
        from shared.dtos import UnifiedPublicDetailDTO

        dto = UnifiedPublicDetailDTO(
            uuid="test-uuid",
            slug="test-slug",
            module_type="renting",
        )

        self.assertEqual(dto.uuid, "test-uuid")
        self.assertEqual(dto.slug, "test-slug")
        self.assertEqual(dto.module_type, "renting")

    def test_dto_serialization(self):
        """Verifica que el DTO se puede serializar a dict."""
        from shared.dtos import UnifiedPublicDetailDTO
        from dataclasses import asdict

        dto = UnifiedPublicDetailDTO(
            uuid="test-uuid",
            slug="test-slug",
            module_type="shop",
        )

        dto_dict = asdict(dto)
        self.assertIsInstance(dto_dict, dict)
        self.assertEqual(dto_dict['uuid'], "test-uuid")
        self.assertEqual(dto_dict['module_type'], "shop")
