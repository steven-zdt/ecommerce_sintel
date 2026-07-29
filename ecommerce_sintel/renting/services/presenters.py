"""
Presenters para la página de detalle pública de Equipment.

Los Presenters orquestan DTOs y centralizan TODA la lógica de transformación de datos.
Frontend NUNCA calcula nada — solo renderiza.

Principio: Backend presents data shaped for UI (presentation layer),
Frontend renders data as-is.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.db.models import Avg, Count
from django.utils.text import truncate_words

from renting.models import Equipment, EquipmentVariant
from renting.services.dtos import (
    ImageDTO, TagDTO, BenefitDTO, FeatureDTO, SpecDTO, SpecGroupDTO,
    RequirementDTO, IncludedItemDTO, ExcludedItemDTO, ServiceDTO,
    OptionalServiceDTO, VideoDTO, DocumentDTO, FAQItemDTO, ReviewDTO,
    ReviewsSummaryDTO, CommercialOptionDTO, AvailabilityDTO, LogisticsDTO,
    EquipmentPreviewDTO, SEODTO, EquipmentPricingDTO, EquipmentHeroDTO,
    EquipmentMarketingDTO, EquipmentTechnicalDTO, EquipmentServicesDTO,
    GalleryDTO, EquipmentMediaDTO, EquipmentPublicDetailDTO,
)


# Utilidades de formatos
def format_currency(amount: Optional[Decimal]) -> str:
    """Formatea moneda colombiana: "$2.950.000" """
    if amount is None:
        return ""

    # Convertir a int para formatting
    amount_int = int(amount)

    # Format con separadores de miles
    formatted = f"{amount_int:,}".replace(",", ".")
    return f"${formatted}"


def resolve_tag_display(tag_code: str) -> TagDTO:
    """Resuelve el display de un tag comercial.

    Maps tag code (OFERTA, NUEVO, etc.) to display info.
    """
    TAG_MAPPING = {
        'OFERTA': TagDTO(code='OFERTA', label='OFERTA', color='danger'),
        'NUEVO': TagDTO(code='NUEVO', label='NUEVO', color='info'),
        'POPULAR': TagDTO(code='POPULAR', label='POPULAR', color='warning'),
        'PROMOCION': TagDTO(code='PROMOCION', label='PROMOCIÓN', color='danger'),
        'DESCUENTO': TagDTO(code='DESCUENTO', label='DESCUENTO', color='success'),
        'HOT': TagDTO(code='HOT', label='🔥 HOT', color='danger'),
    }
    return TAG_MAPPING.get(tag_code, TagDTO(code=tag_code, label=tag_code, color='secondary'))


# ─── Presenters ────────────────────────────────────────────────────────────

class EquipmentPricingPresenter:
    """Presenta pricing de equipo de forma comercial.

    Centraliza TODOS los cálculos de precio.
    Frontend nunca calcula nada.
    """

    def __init__(self, variant: Optional[EquipmentVariant],
                 marketing_config: Optional[Dict] = None,
                 cost_rules: Optional[List] = None):
        self.variant = variant
        self.marketing_config = marketing_config or {}
        self.cost_rules = cost_rules or []

    def present(self) -> EquipmentPricingDTO:
        """Retorna DTO lista para renderizar."""
        if not self.variant:
            return EquipmentPricingDTO()

        # Obtener precios base
        price_per_day = self.variant.rental_price_per_day or Decimal("0")
        price_per_hour = self.variant.rental_price_per_hour or Decimal("0")

        # Obtener precios de marketing
        reference_price = self.marketing_config.get('reference_price') or price_per_day
        promo_price = self.marketing_config.get('promo_price') or reference_price

        # Calcular descuento
        if reference_price and promo_price:
            try:
                discount_pct = int((reference_price - promo_price) / reference_price * 100) if reference_price > 0 else 0
                discount_amt = reference_price - promo_price
            except (ZeroDivisionError, TypeError):
                discount_pct = 0
                discount_amt = Decimal("0")
        else:
            discount_pct = 0
            discount_amt = Decimal("0")

        has_promotion = promo_price < reference_price if (promo_price and reference_price) else False

        return EquipmentPricingDTO(
            price_per_day=price_per_day,
            price_per_hour=price_per_hour,
            formatted_price_per_day=format_currency(price_per_day),
            formatted_price_per_hour=format_currency(price_per_hour),
            reference_price=reference_price,
            promo_price=promo_price,
            formatted_reference_price=format_currency(reference_price),
            formatted_promo_price=format_currency(promo_price),
            discount_percentage=discount_pct,
            discount_amount=discount_amt,
            formatted_discount_amount=format_currency(discount_amt),
            has_promotion=has_promotion,
            saving_message=f"Ahorras {format_currency(discount_amt)}" if discount_amt > 0 else "",
            components=self._build_components(price_per_day, reference_price),
            currency_code="COP",
            currency_symbol="$",
        )

    def _build_components(self, base_price: Decimal, total: Decimal) -> List[Dict[str, Any]]:
        """Arma desglose de costos para mostrar."""
        components = []
        if base_price:
            components.append({
                "label": "Precio base",
                "amount": format_currency(base_price),
                "bold": False,
            })

        if total and total != base_price:
            tax_amount = total - base_price
            if tax_amount > 0:
                components.append({
                    "label": "Impuesto (19%)",
                    "amount": f"+{format_currency(tax_amount)}",
                    "bold": False,
                })

        if total:
            components.append({
                "label": "TOTAL",
                "amount": format_currency(total),
                "bold": True,
            })

        return components


class EquipmentPublicDetailPresenter:
    """Presenta un equipo completo para detalle público.

    Orquesta todos los DTOs anteriores en uno solo.
    Llamado desde endpoint GET /equipment/{uuid}/detail/
    """

    def __init__(self, equipment: Equipment, user=None):
        self.equipment = equipment
        self.user = user

    def present(self) -> EquipmentPublicDetailDTO:
        """Retorna DTO completo, listo para frontend."""

        # Obtener variante principal (primera activa)
        main_variant = self.equipment.variants.filter(is_active=True).first()

        # Orquestar todos los DTOs
        return EquipmentPublicDetailDTO(
            uuid=str(self.equipment.uuid),
            slug=self.equipment.slug,

            hero=self._present_hero(main_variant),
            pricing=self._present_pricing(main_variant),
            marketing=self._present_marketing(),
            technical=self._present_technical(),
            services=self._present_services(),
            media=self._present_media(),
            faqs=self._present_faqs(),
            reviews=self._present_reviews(),
            availability=self._present_availability(main_variant),
            commercial_options=self._present_commercial_options(),
            logistics=self._present_logistics(),
            related_equipment=self._present_related(),
            seo=self._present_seo(),
        )

    def _present_hero(self, variant: Optional[EquipmentVariant]) -> Optional[EquipmentHeroDTO]:
        """Presenta hero section."""
        if not variant:
            return None

        # Obtener imagen principal
        primary_image = self.equipment.images.filter(is_primary=True).first()
        hero_image = None
        if primary_image:
            hero_image = ImageDTO(
                url=primary_image.image.url,
                alt_text=primary_image.alt_text or self.equipment.name,
                image_type=primary_image.image_type,
            )

        # Rating
        reviews = self.equipment.reviews.all()
        rating_avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        rating_count = reviews.count()
        rating_display = f"{rating_avg:.1f} ⭐ ({rating_count} reseñas)" if rating_count > 0 else ""

        # Pricing
        marketing = getattr(self.equipment, 'marketing', None)
        marketing_config = {}
        if marketing:
            marketing_config = {
                'reference_price': marketing.reference_price,
                'promo_price': marketing.promo_price,
            }

        pricing_presenter = EquipmentPricingPresenter(variant, marketing_config)
        pricing_dto = pricing_presenter.present()

        # Disponibilidad
        availability_label = "Disponible ahora" if self.equipment.is_active else "No disponible"
        availability_detail = f"{variant.stock} unidad(es) en stock"

        return EquipmentHeroDTO(
            name=self.equipment.name,
            brand_name=self.equipment.brand.name if self.equipment.brand else "",
            category_name=self.equipment.category.name if self.equipment.category else "",
            description=self.equipment.description or "",
            hero_image=hero_image,
            is_active=self.equipment.is_active,
            is_featured=self.equipment.is_featured,
            availability_status="available" if self.equipment.is_active else "unavailable",
            availability_label=availability_label,
            availability_detail=availability_detail,
            rating_average=float(rating_avg),
            rating_count=rating_count,
            rating_display=rating_display,
            pricing=pricing_dto,
            cta_label=getattr(marketing, 'cta_label', 'Reservar ahora') if marketing else 'Reservar ahora',
            cta_enabled=self.equipment.is_active,
            cta_disabled_reason="" if self.equipment.is_active else "Equipo no disponible",
        )

    def _present_pricing(self, variant: Optional[EquipmentVariant]) -> Optional[EquipmentPricingDTO]:
        """Usa EquipmentPricingPresenter."""
        if not variant:
            return None

        marketing = getattr(self.equipment, 'marketing', None)
        marketing_config = {}
        if marketing:
            marketing_config = {
                'reference_price': marketing.reference_price,
                'promo_price': marketing.promo_price,
            }

        presenter = EquipmentPricingPresenter(variant, marketing_config)
        return presenter.present()

    def _present_marketing(self) -> Optional[EquipmentMarketingDTO]:
        """Presenta marketing info."""
        marketing = getattr(self.equipment, 'marketing', None)
        if not marketing:
            return None

        # Resolver tags
        tags = []
        if hasattr(marketing, 'tags') and marketing.tags:
            for tag_code in marketing.tags:
                tags.append(resolve_tag_display(tag_code))

        # Quick benefits
        quick_benefits = []
        if hasattr(marketing, 'quick_benefits') and marketing.quick_benefits:
            for benefit in marketing.quick_benefits:
                quick_benefits.append(BenefitDTO(
                    icon=benefit.get('icon', 'bi-check-circle'),
                    label=benefit.get('label', ''),
                ))

        return EquipmentMarketingDTO(
            tags=tags,
            featured_benefit=getattr(marketing, 'featured_benefit', '') or '',
            main_message=getattr(marketing, 'main_message', '') or '',
            trust_message=getattr(marketing, 'trust_message', '') or '',
            urgency_message=getattr(marketing, 'urgency_message', '') or '',
            social_proof_message=getattr(marketing, 'social_proof_message', '') or '',
            quick_benefits=quick_benefits,
            use_cases=getattr(marketing, 'use_cases', []) or [],
            purchase_price_reference=getattr(marketing, 'purchase_price_reference', None),
            financial_message=getattr(marketing, 'financial_message', '') or '',
            promo_banner_message=getattr(marketing, 'promo_banner_message', '') or '',
        )

    def _present_technical(self) -> Optional[EquipmentTechnicalDTO]:
        """Presenta especificaciones técnicas."""
        features = []
        for feature in self.equipment.features.filter(is_active=True):
            features.append(FeatureDTO(
                title=feature.title,
                value=feature.value,
                icon=getattr(feature, 'icon', None),
            ))

        spec_groups = []
        for group in self.equipment.specification_groups.filter(is_active=True):
            specs = []
            for spec in group.specifications.filter(is_active=True):
                specs.append(SpecDTO(
                    name=spec.name,
                    value=spec.value,
                ))
            spec_groups.append(SpecGroupDTO(name=group.name, specs=specs))

        requirements = []
        for req in self.equipment.requirements.filter(is_active=True):
            requirements.append(RequirementDTO(
                title=req.title,
                description=req.description,
            ))

        return EquipmentTechnicalDTO(
            features=features,
            specification_groups=spec_groups,
            requirements=requirements,
        )

    def _present_services(self) -> Optional[EquipmentServicesDTO]:
        """Presenta servicios incluidos/opcionales."""
        included_items = []
        for item in self.equipment.included_items.filter(is_active=True):
            included_items.append(IncludedItemDTO(
                title=item.title,
                description=item.description,
                icon=getattr(item, 'icon', None),
            ))

        excluded_items = []
        for item in self.equipment.excluded_items.filter(is_active=True):
            excluded_items.append(ExcludedItemDTO(
                title=item.title,
                description=item.description,
                icon=getattr(item, 'icon', None),
            ))

        optional_services = []
        for service in self.equipment.optional_services.filter(is_active=True):
            optional_services.append(OptionalServiceDTO(
                title=service.title,
                description=service.description,
                price=service.price or Decimal("0"),
                formatted_price=format_currency(service.price),
                icon=getattr(service, 'icon', None),
            ))

        services_included = []
        for service in self.equipment.services_included.filter(is_active=True):
            services_included.append(ServiceDTO(
                title=service.title,
                description=service.description,
                icon=getattr(service, 'icon', None),
            ))

        return EquipmentServicesDTO(
            included_items=included_items,
            excluded_items=excluded_items,
            optional_services=optional_services,
            services_included=services_included,
        )

    def _present_media(self) -> Optional[EquipmentMediaDTO]:
        """Presenta videos, documentos, imágenes."""
        # Galería
        gallery = GalleryDTO()

        primary = self.equipment.images.filter(is_primary=True).first()
        if primary:
            gallery.principal = ImageDTO(
                url=primary.image.url,
                alt_text=primary.alt_text or self.equipment.name,
                image_type=primary.image_type,
            )

        for img in self.equipment.images.filter(is_active=True):
            img_dto = ImageDTO(
                url=img.image.url,
                alt_text=img.alt_text or f"{self.equipment.name} - {img.image_type}",
                image_type=img.image_type,
            )
            gallery.all_images.append(img_dto)

            if img.image_type == 'INSTALACION':
                gallery.installation_images.append(img_dto)
            elif img.image_type == 'DETALLE':
                gallery.detail_images.append(img_dto)
            elif img.image_type == 'VISTA_360':
                gallery.view_360_images.append(img_dto)
            elif img.image_type in ['PRINCIPAL', 'GALERIA']:
                gallery.principal_images.append(img_dto)

        # Videos
        videos = []
        for video in self.equipment.videos.filter(is_active=True):
            videos.append(VideoDTO(
                title=video.title,
                source_type=video.source_type,
                video_url=video.video_url,
                thumbnail=getattr(video, 'thumbnail', None),
            ))

        # Documentos
        documents = []
        for doc in self.equipment.documents.filter(is_active=True, is_public=True):
            documents.append(DocumentDTO(
                title=doc.title,
                description=doc.description,
                document_type=doc.document_type,
                download_url=doc.file.url if doc.file else '',
                version=getattr(doc, 'version', None),
                download_count=getattr(doc, 'downloads', 0),
            ))

        return EquipmentMediaDTO(
            gallery=gallery,
            videos=videos,
            documents=documents,
        )

    def _present_faqs(self) -> List[FAQItemDTO]:
        """Presenta FAQ."""
        faqs = []
        for faq in self.equipment.faqs.filter(is_active=True):
            faqs.append(FAQItemDTO(
                question=faq.question,
                answer=faq.answer,
            ))
        return faqs

    def _present_reviews(self) -> Optional[ReviewsSummaryDTO]:
        """Presenta resumen de reviews."""
        reviews = self.equipment.reviews.all()

        if not reviews.exists():
            return None

        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        total_count = reviews.count()

        # Breakdown por rating
        breakdown = {}
        for i in range(1, 6):
            breakdown[i] = reviews.filter(rating=i).count()

        # Reviews items (últimos 10)
        review_items = []
        for review in reviews.order_by('-created_at')[:10]:
            review_items.append(ReviewDTO(
                user_name=review.user.email.split('@')[0],
                rating=review.rating,
                comment=truncate_words(review.comment, 30),
                created_at=review.created_at.isoformat(),
            ))

        return ReviewsSummaryDTO(
            average_rating=float(avg_rating),
            total_count=total_count,
            rating_breakdown=breakdown,
            items=review_items,
        )

    def _present_availability(self, variant: Optional[EquipmentVariant]) -> Optional[AvailabilityDTO]:
        """Presenta estado de disponibilidad."""
        if not variant:
            return None

        status = "available" if self.equipment.is_active and variant.stock > 0 else "unavailable"

        if status == "available" and variant.stock <= 5:
            status = "limited"

        status_labels = {
            "available": "Disponible ahora",
            "limited": "Stock limitado",
            "unavailable": "No disponible",
        }

        return AvailabilityDTO(
            status=status,
            status_label=status_labels.get(status, ""),
            status_detail=f"{variant.stock} unidad(es) en stock",
            total_stock=variant.stock,
            available_now=variant.stock if self.equipment.is_active else 0,
        )

    def _present_commercial_options(self) -> List[CommercialOptionDTO]:
        """Presenta opciones comerciales (Renting vs Comodato)."""
        options = []

        commercial_config = getattr(self.equipment, 'commercial_config', None)
        if commercial_config:
            if commercial_config.renting_enabled:
                options.append(CommercialOptionDTO(
                    modality="renting",
                    enabled=True,
                ))

            if commercial_config.comodato_enabled:
                # Obtener términos disponibles
                terms = self.equipment.commercial_options.filter(
                    modality='COMODATO',
                    is_enabled=True
                ).values_list('term_months', flat=True).distinct().order_by('term_months')

                options.append(CommercialOptionDTO(
                    modality="comodato",
                    enabled=True,
                    terms=list(terms),
                ))
        else:
            # Default: solo Renting
            options.append(CommercialOptionDTO(
                modality="renting",
                enabled=True,
            ))

        return options

    def _present_logistics(self) -> Optional[LogisticsDTO]:
        """Presenta costos de logística."""
        logistics = getattr(self.equipment, 'logistics_config', None)
        if not logistics:
            return None

        return LogisticsDTO(
            delivery_cost=logistics.delivery_cost,
            pickup_cost=logistics.pickup_cost,
            installation_cost=logistics.installation_cost,
            calibration_cost=logistics.calibration_cost,
            training_cost=logistics.training_cost,
            startup_cost=logistics.startup_cost,
            formatted_delivery=format_currency(logistics.delivery_cost),
            formatted_pickup=format_currency(logistics.pickup_cost),
            formatted_installation=format_currency(logistics.installation_cost),
            formatted_total=format_currency(
                (logistics.delivery_cost or Decimal("0")) +
                (logistics.pickup_cost or Decimal("0"))
            ),
        )

    def _present_related(self) -> List[EquipmentPreviewDTO]:
        """Presenta equipos relacionados (misma categoría)."""
        related = []

        related_items = self.equipment.category.equipments.filter(
            is_active=True
        ).exclude(uuid=self.equipment.uuid).order_by('-created_at')[:6]

        for eq in related_items:
            variant = eq.variants.filter(is_active=True).first()
            if variant:
                price_from = format_currency(variant.rental_price_per_day)

                img = eq.images.filter(is_primary=True).first()
                image_url = img.image.url if img else ''

                related.append(EquipmentPreviewDTO(
                    uuid=str(eq.uuid),
                    name=eq.name,
                    image_url=image_url,
                    price_from=price_from,
                ))

        return related

    def _present_seo(self) -> Optional[SEODTO]:
        """Presenta SEO metadata."""
        return SEODTO(
            meta_title=self.equipment.meta_title or self.equipment.name,
            meta_description=self.equipment.meta_description or truncate_words(self.equipment.description, 20),
            meta_keywords=self.equipment.meta_keywords,
            og_image_url=self.equipment.og_image.url if self.equipment.og_image else None,
        )
