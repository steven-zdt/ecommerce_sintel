"""
Unified Data Transfer Objects (DTOs) para páginas de detalle pública.

Usado por: Renting, Shop, Technical Services

Estos DTOs presentan la información de manera estructurada y lista para renderizar,
evitando que el frontend tenga que hacer cálculos o transformaciones de datos.

Interfaz común para todos los módulos públicos.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date


@dataclass
class ImageDTO:
    url: str
    alt_text: str = ""
    image_type: str = "GALERIA"


@dataclass
class TagDTO:
    code: str
    label: str
    color: str


@dataclass
class BenefitDTO:
    icon: str
    label: str


@dataclass
class FeatureDTO:
    title: str
    value: str
    icon: Optional[str] = None


@dataclass
class SpecDTO:
    name: str
    value: str


@dataclass
class SpecGroupDTO:
    name: str
    specs: List[SpecDTO] = field(default_factory=list)


@dataclass
class RequirementDTO:
    title: str
    description: str


@dataclass
class IncludedItemDTO:
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class ExcludedItemDTO:
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class ServiceDTO:
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class OptionalServiceDTO:
    title: str
    description: str
    price: Decimal
    formatted_price: str
    icon: Optional[str] = None


@dataclass
class VideoDTO:
    title: str
    source_type: str
    video_url: str
    thumbnail: Optional[str] = None


@dataclass
class DocumentDTO:
    title: str
    description: str
    document_type: str
    download_url: str
    version: Optional[str] = None
    download_count: int = 0


@dataclass
class FAQItemDTO:
    question: str
    answer: str


@dataclass
class ReviewDTO:
    user_name: str
    rating: int
    comment: str
    created_at: str
    helpful_count: int = 0


@dataclass
class ReviewsSummaryDTO:
    average_rating: float
    total_count: int
    rating_breakdown: Dict[int, int]
    items: List[ReviewDTO] = field(default_factory=list)


@dataclass
class AvailabilityDTO:
    status: str
    status_label: str
    status_detail: str
    total_stock: int
    available_now: int
    next_available_date: Optional[date] = None


@dataclass
class RelatedItemDTO:
    uuid: str
    name: str
    image_url: str
    price_from: str


@dataclass
class RecommendationDTO:
    title: str
    items: List[RelatedItemDTO] = field(default_factory=list)
    recommendation_type: str = "related"


@dataclass
class PricingDTO:
    price_per_day: Optional[Decimal] = None
    price_per_hour: Optional[Decimal] = None
    formatted_price_per_day: str = ""
    formatted_price_per_hour: str = ""
    reference_price: Optional[Decimal] = None
    promo_price: Optional[Decimal] = None
    formatted_reference_price: str = ""
    formatted_promo_price: str = ""
    discount_percentage: int = 0
    discount_amount: Decimal = Decimal("0")
    formatted_discount_amount: str = ""
    has_promotion: bool = False
    saving_message: str = ""
    components: List[Dict[str, Any]] = field(default_factory=list)
    currency_code: str = "COP"
    currency_symbol: str = "$"


@dataclass
class HeroDTO:
    name: str
    brand_name: str = ""
    category_name: str = ""
    description: str = ""
    hero_image: Optional[ImageDTO] = None
    is_active: bool = True
    is_featured: bool = False
    availability_status: str = "available"
    availability_label: str = ""
    availability_detail: str = ""
    rating_average: float = 0.0
    rating_count: int = 0
    rating_display: str = ""
    pricing: Optional[PricingDTO] = None
    cta_label: str = "Ver detalles"
    cta_enabled: bool = True
    cta_disabled_reason: str = ""


@dataclass
class MarketingDTO:
    tags: List[TagDTO] = field(default_factory=list)
    featured_benefit: str = ""
    main_message: str = ""
    trust_message: str = ""
    urgency_message: str = ""
    social_proof_message: str = ""
    quick_benefits: List[BenefitDTO] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    purchase_price_reference: Optional[Decimal] = None
    financial_message: str = ""
    savings_vs_purchase_pct: int = 0
    promo_banner_message: str = ""


@dataclass
class TechnicalDTO:
    features: List[FeatureDTO] = field(default_factory=list)
    specification_groups: List[SpecGroupDTO] = field(default_factory=list)
    requirements: List[RequirementDTO] = field(default_factory=list)


@dataclass
class DescriptionDTO:
    short_description: str = ""
    long_description: str = ""
    highlights: List[str] = field(default_factory=list)


@dataclass
class GalleryDTO:
    principal: Optional[ImageDTO] = None
    principal_images: List[ImageDTO] = field(default_factory=list)
    installation_images: List[ImageDTO] = field(default_factory=list)
    detail_images: List[ImageDTO] = field(default_factory=list)
    view_360_images: List[ImageDTO] = field(default_factory=list)
    all_images: List[ImageDTO] = field(default_factory=list)


@dataclass
class SEODTO:
    meta_title: str
    meta_description: str
    meta_keywords: str
    og_image_url: Optional[str] = None


@dataclass
class UnifiedPublicDetailDTO:
    """
    DTO ÚNICO que agrupa TODA la información pública para detail pages.

    Usado por: Renting, Shop, Technical Services

    Reemplaza múltiples requests/parsing en frontend.
    Backend garantiza que cada DTO está 100% completo y listo.
    Frontend nunca calcula nada.
    """
    uuid: str
    slug: str
    module_type: str

    hero: Optional[HeroDTO] = None
    gallery: Optional[GalleryDTO] = None
    pricing: Optional[PricingDTO] = None
    marketing: Optional[MarketingDTO] = None
    availability: Optional[AvailabilityDTO] = None
    description: Optional[DescriptionDTO] = None
    technical: Optional[TechnicalDTO] = None

    included_items: List[IncludedItemDTO] = field(default_factory=list)
    excluded_items: List[ExcludedItemDTO] = field(default_factory=list)
    requirements: List[RequirementDTO] = field(default_factory=list)

    faq: List[FAQItemDTO] = field(default_factory=list)
    documents: List[DocumentDTO] = field(default_factory=list)
    videos: List[VideoDTO] = field(default_factory=list)

    reviews: Optional[ReviewsSummaryDTO] = None
    related_items: List[RelatedItemDTO] = field(default_factory=list)
    recommendations: List[RecommendationDTO] = field(default_factory=list)

    seo: Optional[SEODTO] = None
