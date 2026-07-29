"""
Data Transfer Objects (DTOs) para la página de detalle pública de Equipment.

Estos DTOs presentan la información de manera estructurada y lista para renderizar,
evitando que el frontend tenga que hacer cálculos o transformaciones de datos.

Cada DTO es responsable de un aspecto específico del detalle del equipo.
El DTO principal (EquipmentPublicDetailDTO) agrupa todos los demás.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date


# ─── DTOs Primitivos ───────────────────────────────────────────────────────

@dataclass
class ImageDTO:
    """Representa una imagen con metadata."""
    url: str
    alt_text: str = ""
    image_type: str = "GALERIA"


@dataclass
class TagDTO:
    """Badge comercial: OFERTA, NUEVO, POPULAR, etc."""
    code: str
    label: str
    color: str  # "danger", "info", "warning", "success"


@dataclass
class BenefitDTO:
    """Beneficio rápido: ["Transporte", "Instalación", ...]"""
    icon: str  # "bi-truck", "bi-wrench", etc
    label: str


@dataclass
class FeatureDTO:
    """Característica destacada: "Potencia: 20T"."""
    title: str
    value: str
    icon: Optional[str] = None


@dataclass
class SpecDTO:
    """Especificación técnica: name + value."""
    name: str
    value: str


@dataclass
class SpecGroupDTO:
    """Grupo de especificaciones: "Motor", "Hidráulico", etc."""
    name: str
    specs: List[SpecDTO] = field(default_factory=list)


@dataclass
class RequirementDTO:
    """Requisito para poder rentar el equipo."""
    title: str
    description: str


@dataclass
class IncludedItemDTO:
    """Qué incluye el alquiler."""
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class ExcludedItemDTO:
    """Qué NO incluye el alquiler."""
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class ServiceDTO:
    """Servicio incluido en el precio."""
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class OptionalServiceDTO:
    """Servicio adicional con costo extra."""
    title: str
    description: str
    price: Decimal
    formatted_price: str
    icon: Optional[str] = None


@dataclass
class VideoDTO:
    """Video del equipo: YouTube, Vimeo, o MP4."""
    title: str
    source_type: str  # "youtube", "vimeo", "mp4"
    video_url: str
    thumbnail: Optional[str] = None


@dataclass
class DocumentDTO:
    """Documento descargable: manual, certificado, etc."""
    title: str
    description: str
    document_type: str  # "manual", "certificado", etc
    download_url: str
    version: Optional[str] = None
    download_count: int = 0


@dataclass
class FAQItemDTO:
    """Pregunta frecuente."""
    question: str
    answer: str


@dataclass
class ReviewDTO:
    """Reseña de un usuario."""
    user_name: str
    rating: int  # 1-5
    comment: str
    created_at: str  # ISO date
    helpful_count: int = 0


@dataclass
class ReviewsSummaryDTO:
    """Resumen de reseñas."""
    average_rating: float
    total_count: int
    rating_breakdown: Dict[int, int]  # {1: 2, 2: 3, 3: 5, 4: 10, 5: 30}
    items: List[ReviewDTO] = field(default_factory=list)


@dataclass
class CommercialOptionDTO:
    """Opción comercial: Renting o Comodato."""
    modality: str  # "renting", "comodato"
    enabled: bool
    terms: Optional[List[int]] = None  # [6, 12, 18, 24, 36] para comodato


@dataclass
class AvailabilityDTO:
    """Estado de disponibilidad."""
    status: str  # "available", "limited", "unavailable"
    status_label: str  # "Disponible ahora"
    status_detail: str  # "5 unidades en stock"
    total_stock: int
    available_now: int
    next_available_date: Optional[date] = None


@dataclass
class LogisticsDTO:
    """Costos de logística."""
    delivery_cost: Optional[Decimal] = None
    pickup_cost: Optional[Decimal] = None
    installation_cost: Optional[Decimal] = None
    calibration_cost: Optional[Decimal] = None
    training_cost: Optional[Decimal] = None
    startup_cost: Optional[Decimal] = None

    # Formatted versions
    formatted_delivery: str = ""
    formatted_pickup: str = ""
    formatted_installation: str = ""
    formatted_total: str = ""


@dataclass
class EquipmentPreviewDTO:
    """Preview de equipo relacionado."""
    uuid: str
    name: str
    image_url: str
    price_from: str  # "$2.950.000"


@dataclass
class SEODTO:
    """SEO metadata."""
    meta_title: str
    meta_description: str
    meta_keywords: str
    og_image_url: Optional[str] = None


# ─── DTOs Principales ──────────────────────────────────────────────────────

@dataclass
class EquipmentPricingDTO:
    """Presentación unificada de pricing.

    TODOS los cálculos de precio se hacen en backend.
    Frontend solo renderiza.
    """
    # Precios base (desde variante)
    price_per_day: Optional[Decimal] = None
    price_per_hour: Optional[Decimal] = None

    # Strings formateados
    formatted_price_per_day: str = ""
    formatted_price_per_hour: str = ""

    # Marketing pricing
    reference_price: Optional[Decimal] = None  # Precio anterior
    promo_price: Optional[Decimal] = None      # Precio actual
    formatted_reference_price: str = ""
    formatted_promo_price: str = ""

    # Descuento calculado
    discount_percentage: int = 0
    discount_amount: Decimal = Decimal("0")
    formatted_discount_amount: str = ""

    # Display helpers
    has_promotion: bool = False
    saving_message: str = ""

    # Componentes de precio (desglose)
    components: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata de moneda
    currency_code: str = "COP"
    currency_symbol: str = "$"


@dataclass
class EquipmentHeroDTO:
    """Hero section: imagen + metadata + pricing + CTA.

    Todo lo que se ve en el fold inicial.
    """
    # Identidad
    name: str
    brand_name: str = ""
    category_name: str = ""
    description: str = ""

    # Imagen principal
    hero_image: Optional[ImageDTO] = None

    # Estado
    is_active: bool = True
    is_featured: bool = False
    availability_status: str = "available"
    availability_label: str = ""
    availability_detail: str = ""

    # Rating
    rating_average: float = 0.0
    rating_count: int = 0
    rating_display: str = ""

    # Pricing
    pricing: Optional[EquipmentPricingDTO] = None

    # CTA
    cta_label: str = "Reservar ahora"
    cta_enabled: bool = True
    cta_disabled_reason: str = ""


@dataclass
class EquipmentMarketingDTO:
    """Información comercial/persuasiva."""
    # Tags comerciales
    tags: List[TagDTO] = field(default_factory=list)

    # Mensajes de conversión
    featured_benefit: str = ""
    main_message: str = ""
    trust_message: str = ""
    urgency_message: str = ""
    social_proof_message: str = ""

    # Quick benefits
    quick_benefits: List[BenefitDTO] = field(default_factory=list)

    # Use cases
    use_cases: List[str] = field(default_factory=list)

    # Comparativa compra vs alquiler
    purchase_price_reference: Optional[Decimal] = None
    financial_message: str = ""
    savings_vs_purchase_pct: int = 0

    # Promo banner
    promo_banner_message: str = ""


@dataclass
class EquipmentTechnicalDTO:
    """Especificaciones técnicas."""
    # Características destacadas
    features: List[FeatureDTO] = field(default_factory=list)

    # Especificaciones agrupadas
    specification_groups: List[SpecGroupDTO] = field(default_factory=list)

    # Requisitos
    requirements: List[RequirementDTO] = field(default_factory=list)


@dataclass
class EquipmentServicesDTO:
    """Servicios: incluidos vs opcionales."""
    # Alcance del alquiler
    included_items: List[IncludedItemDTO] = field(default_factory=list)
    excluded_items: List[ExcludedItemDTO] = field(default_factory=list)

    # Servicios adicionales (costo extra)
    optional_services: List[OptionalServiceDTO] = field(default_factory=list)

    # Servicios incluidos en precio
    services_included: List[ServiceDTO] = field(default_factory=list)


@dataclass
class GalleryDTO:
    """Galería organizada por tipo de imagen."""
    principal: Optional[ImageDTO] = None
    principal_images: List[ImageDTO] = field(default_factory=list)
    installation_images: List[ImageDTO] = field(default_factory=list)
    detail_images: List[ImageDTO] = field(default_factory=list)
    view_360_images: List[ImageDTO] = field(default_factory=list)
    all_images: List[ImageDTO] = field(default_factory=list)


@dataclass
class EquipmentMediaDTO:
    """Videos, documentos, imágenes."""
    gallery: Optional[GalleryDTO] = None
    videos: List[VideoDTO] = field(default_factory=list)
    documents: List[DocumentDTO] = field(default_factory=list)


@dataclass
class EquipmentPublicDetailDTO:
    """DTO ÚNICO que agrupa TODA la información pública.

    Reemplaza múltiples requests/parsing en frontend.
    Backend garantiza que cada DTO está 100% completo y listo.
    Frontend nunca calcula nada.
    """
    # Identidad
    uuid: str
    slug: str

    # Sections (DTOs anteriores)
    hero: Optional[EquipmentHeroDTO] = None
    pricing: Optional[EquipmentPricingDTO] = None
    marketing: Optional[EquipmentMarketingDTO] = None
    technical: Optional[EquipmentTechnicalDTO] = None
    services: Optional[EquipmentServicesDTO] = None
    media: Optional[EquipmentMediaDTO] = None

    # FAQ
    faqs: List[FAQItemDTO] = field(default_factory=list)

    # Reviews
    reviews: Optional[ReviewsSummaryDTO] = None

    # Availability
    availability: Optional[AvailabilityDTO] = None

    # Commercial modalities
    commercial_options: List[CommercialOptionDTO] = field(default_factory=list)

    # Logistics (costos)
    logistics: Optional[LogisticsDTO] = None

    # Related equipment
    related_equipment: List[EquipmentPreviewDTO] = field(default_factory=list)

    # SEO
    seo: Optional[SEODTO] = None
