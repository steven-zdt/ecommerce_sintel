"""
Presenters unificados para páginas de detalle pública.

Patrón Enterprise: toda lógica de transformación vive en presenters, no en ViewSets.
Frontend solo renderiza.

Usado por: Renting, Shop, Technical Services
"""

from abc import ABC, abstractmethod
from shared.dtos import UnifiedPublicDetailDTO


class PublicDetailPresenterBase(ABC):
    """
    Clase base para todos los presenters de detalle pública.

    Cada módulo (Renting, Shop, Services) hereda e implementa present().
    Garantiza contrato unificado.
    """

    def __init__(self, item, user=None):
        self.item = item
        self.user = user

    @abstractmethod
    def present(self) -> UnifiedPublicDetailDTO:
        raise NotImplementedError("Subclasses must implement present()")


class RentingPublicDetailPresenter(PublicDetailPresenterBase):
    """
    Convierte Equipment → UnifiedPublicDetailDTO

    Reutiliza lógica de EquipmentPublicDetailPresenter de renting/services/presenters.py
    pero normaliza a formato unificado.
    """

    def present(self) -> UnifiedPublicDetailDTO:
        from renting.services.presenters import EquipmentPublicDetailPresenter
        from shared.dtos.public_detail import UnifiedPublicDetailDTO

        renting_presenter = EquipmentPublicDetailPresenter(self.item, user=self.user)
        renting_dto = renting_presenter.present()

        return UnifiedPublicDetailDTO(
            uuid=str(self.item.uuid),
            slug=self.item.slug,
            module_type="renting",
            hero=renting_dto.hero,
            gallery=renting_dto.media.gallery if renting_dto.media else None,
            pricing=renting_dto.pricing,
            marketing=renting_dto.marketing,
            availability=renting_dto.availability,
            description=None,
            technical=renting_dto.technical,
            included_items=renting_dto.services.included_items if renting_dto.services else [],
            excluded_items=renting_dto.services.excluded_items if renting_dto.services else [],
            requirements=renting_dto.technical.requirements if renting_dto.technical else [],
            faq=renting_dto.faqs,
            documents=renting_dto.media.documents if renting_dto.media else [],
            videos=renting_dto.media.videos if renting_dto.media else [],
            reviews=renting_dto.reviews,
            related_items=renting_dto.related_equipment,
            recommendations=[],
            seo=renting_dto.seo,
        )


class ShopPublicDetailPresenter(PublicDetailPresenterBase):
    """
    Convierte Product → UnifiedPublicDetailDTO

    Extrae data de Product model y expone en formato unificado.
    TODO: Implementar cuando Shop tenga Presenter propio.
    """

    def present(self) -> UnifiedPublicDetailDTO:
        from shared.dtos.public_detail import (
            UnifiedPublicDetailDTO, HeroDTO, PricingDTO, GalleryDTO,
            ImageDTO, ReviewsSummaryDTO, RelatedItemDTO
        )
        from decimal import Decimal

        images = []
        principal_img = None
        if hasattr(self.item, 'images') and self.item.images.exists():
            for img in self.item.images.all():
                img_dto = ImageDTO(
                    url=img.image.url,
                    alt_text=img.alt_text or self.item.name,
                    image_type="GALERIA"
                )
                images.append(img_dto)
                if img.is_primary:
                    principal_img = img_dto

        pricing = None
        if self.item.variants.exists():
            variant = self.item.variants.first()
            pricing = PricingDTO(
                price_per_day=None,
                price_per_hour=None,
                promo_price=Decimal(str(variant.price)) if variant.price else None,
                formatted_promo_price=f"${variant.price:,.0f}" if variant.price else "N/A",
                has_promotion=variant.discounted_price is not None if hasattr(variant, 'discounted_price') else False,
            )

        reviews = None
        if hasattr(self.item, 'reviews'):
            review_qs = self.item.reviews.filter(is_deleted=False)
            if review_qs.exists():
                avg_rating = sum(r.rating for r in review_qs) / review_qs.count()
                reviews = ReviewsSummaryDTO(
                    average_rating=avg_rating,
                    total_count=review_qs.count(),
                    rating_breakdown={},
                    items=[]
                )

        return UnifiedPublicDetailDTO(
            uuid=str(self.item.uuid),
            slug=self.item.slug,
            module_type="shop",
            hero=HeroDTO(
                name=self.item.name,
                category_name=self.item.category.name if self.item.category else "",
                brand_name=self.item.brand.name if self.item.brand else "",
                description=self.item.description or "",
                hero_image=principal_img,
                is_active=self.item.is_active,
                is_featured=self.item.is_featured,
                pricing=pricing,
                cta_label="Agregar al carrito",
                cta_enabled=self.item.is_active,
            ),
            gallery=GalleryDTO(
                principal=principal_img,
                all_images=images,
                principal_images=[img for img in images if img.image_type in ["PRINCIPAL", "GALERIA"]],
            ),
            pricing=pricing,
            reviews=reviews,
            seo=None,
        )


class ServicePublicDetailPresenter(PublicDetailPresenterBase):
    """
    Convierte TechnicalService → UnifiedPublicDetailDTO

    Extrae data de TechnicalService model y expone en formato unificado.
    TODO: Implementar cuando Services tenga Presenter propio.
    """

    def present(self) -> UnifiedPublicDetailDTO:
        from shared.dtos.public_detail import (
            UnifiedPublicDetailDTO, HeroDTO, PricingDTO, GalleryDTO,
            ImageDTO, ReviewsSummaryDTO
        )
        from decimal import Decimal

        images = []
        principal_img = None
        if hasattr(self.item, 'images') and self.item.images.exists():
            for img in self.item.images.all():
                img_dto = ImageDTO(
                    url=img.image.url,
                    alt_text=img.alt_text or self.item.name,
                )
                images.append(img_dto)
                if not principal_img:
                    principal_img = img_dto

        pricing = None
        if hasattr(self.item, 'variants') and self.item.variants.exists():
            variant = self.item.variants.first()
            pricing = PricingDTO(
                price_per_day=None,
                price_per_hour=None,
                promo_price=Decimal(str(variant.fixed_price)) if hasattr(variant, 'fixed_price') and variant.fixed_price else None,
                formatted_promo_price=f"${variant.fixed_price:,.0f}" if hasattr(variant, 'fixed_price') and variant.fixed_price else "A cotizar",
            )

        reviews = None
        if hasattr(self.item, 'reviews'):
            review_qs = self.item.reviews.filter(is_deleted=False)
            if review_qs.exists():
                avg_rating = sum(r.rating for r in review_qs) / review_qs.count()
                reviews = ReviewsSummaryDTO(
                    average_rating=avg_rating,
                    total_count=review_qs.count(),
                    rating_breakdown={},
                    items=[]
                )

        return UnifiedPublicDetailDTO(
            uuid=str(self.item.uuid),
            slug=self.item.slug,
            module_type="service",
            hero=HeroDTO(
                name=self.item.name,
                category_name=self.item.category.name if self.item.category else "",
                description=self.item.description or "",
                hero_image=principal_img,
                is_active=self.item.is_active,
                is_featured=self.item.is_featured,
                pricing=pricing,
                cta_label="Solicitar servicio",
                cta_enabled=self.item.is_active,
            ),
            gallery=GalleryDTO(
                principal=principal_img,
                all_images=images,
            ),
            pricing=pricing,
            reviews=reviews,
            seo=None,
        )
