# FASE 2: REDISEÑO DE ARQUITECTURA FRONTEND
## Estructura de Componentes Reutilizables + DTOs + Presenters

**Fecha:** 2026-07-29  
**Objetivo:** Diseñar arquitectura enterprise sin breaking changes  
**Validación:** Mantener compatibilidad total con API existente  

---

## 1. ESTRATEGIA DE NO-BREAKING-CHANGES

### Opción Elegida: Versionamiento de Endpoints

```
ACTUAL (sigue funcionando):
GET /api/v1/equipment/{uuid}/
→ response shape actual (completo pero fragmentado)

NUEVO (agrega info):
GET /api/v1/equipment/{uuid}/detail/
→ response shape unificado via EquipmentPublicDetailDTO

FALLBACK en frontend:
if response.has('detail') → usar nuevo DTO
else → usar parser legado (mantiene compatibilidad)
```

**Beneficio:** 
- API actual NO se toca
- Nuevas integraciones usan `/detail/`
- Frontend elige qué usar via conditional

---

## 2. ESTRUCTURA DE DTOs EN BACKEND

### 2.1 EquipmentPricingDTO

**Ubicación:** `renting/services/presenters.py`

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class EquipmentPricingDTO:
    """Presentación unificada de pricing del equipo.
    
    Todos los cálculos se hacen en backend.
    Frontend solo renderiza.
    """
    # Base prices (desde variante)
    price_per_day: Decimal
    price_per_hour: Decimal
    
    # Formatted strings (para UI)
    formatted_price_per_day: str      # "$2.950.000"
    formatted_price_per_hour: str      # "$122.917"
    
    # Marketing pricing
    reference_price: Decimal           # Precio anterior (original)
    promo_price: Decimal              # Precio actual (con descuento)
    formatted_reference_price: str     # "$4.500.000"
    formatted_promo_price: str         # "$2.950.000"
    
    # Discount calculation
    discount_percentage: int           # 35
    discount_amount: Decimal           # 1.550.000
    formatted_discount_amount: str     # "$1.550.000"
    
    # Display helpers
    has_promotion: bool                # True if promo_price < reference_price
    saving_message: str                # "Ahorras $1.550.000"
    
    # Pricing components (for itemization)
    components: List[Dict]             # [
                                       #   {"label": "Precio base", "amount": "$2.950.000"},
                                       #   {"label": "Impuesto", "amount": "+$590.000"},
                                       # ]
    
    # Currency metadata
    currency_code: str                 # "COP"
    currency_symbol: str               # "$"
    
    @classmethod
    def from_variant_and_marketing(cls, variant, marketing_config, cost_rules):
        """Factory method que calcula TODO.
        
        No permite que frontend haga cálculos.
        """
        # Obtener precio base
        price = variant.rental_price_per_day or variant.rental_price_per_hour
        
        # Aplicar marketing
        promo = marketing_config.promo_price if marketing_config else price
        reference = marketing_config.reference_price if marketing_config else price
        
        # Calcular descuento
        if promo and reference and reference > promo:
            discount_pct = int((reference - promo) / reference * 100)
            discount_amt = reference - promo
        else:
            discount_pct = 0
            discount_amt = 0
        
        # Aplicar cost rules (IVA, etc)
        # ... lógica de cálculo total
        
        return cls(
            price_per_day=variant.rental_price_per_day,
            price_per_hour=variant.rental_price_per_hour,
            formatted_price_per_day=format_currency(price),
            formatted_price_per_hour=format_currency(variant.rental_price_per_hour or 0),
            reference_price=reference,
            promo_price=promo,
            formatted_reference_price=format_currency(reference),
            formatted_promo_price=format_currency(promo),
            discount_percentage=discount_pct,
            discount_amount=discount_amt,
            formatted_discount_amount=format_currency(discount_amt),
            has_promotion=(promo < reference),
            saving_message=f"Ahorras {format_currency(discount_amt)}",
            # ... rest of fields
        )
```

---

### 2.2 EquipmentHeroDTO

```python
@dataclass
class EquipmentHeroDTO:
    """Hero section: imagen + metadata + pricing + CTA.
    
    Todo lo que se ve en el fold inicial.
    """
    # Identidad
    name: str
    brand_name: str
    category_name: str
    description: str
    
    # Imagen principal
    hero_image: ImageDTO                # {"url": "...", "alt": "..."}
    
    # Estado
    is_active: bool
    is_featured: bool
    availability_status: str             # "available" | "limited" | "unavailable"
    availability_label: str              # "Disponible ahora"
    availability_detail: str             # "5 unidades en stock"
    
    # Rating
    rating_average: float                # 4.5
    rating_count: int                    # 42
    rating_display: str                  # "4.5 ⭐ (42 reseñas)"
    
    # Pricing (reutiliza EquipmentPricingDTO)
    pricing: EquipmentPricingDTO
    
    # CTA
    cta_label: str                       # "Reservar ahora" (configurable)
    cta_enabled: bool
    cta_disabled_reason: str             # "Equipo no disponible" if disabled
```

---

### 2.3 EquipmentMarketingDTO

```python
@dataclass
class EquipmentMarketingDTO:
    """Información comercial/persuasiva.
    
    Tags, mensajes, benefits, comparativa.
    """
    # Tags comerciales
    tags: List[TagDTO]                   # [
                                         #   {"code": "OFERTA", "label": "OFERTA", "color": "danger"},
                                         #   {"code": "NUEVO", "label": "NUEVO", "color": "info"},
                                         # ]
    
    # Mensajes de conversión
    featured_benefit: str                # "Ideal para construcción"
    main_message: str                    # "Descripción de la oferta..."
    trust_message: str                   # "Certificado"
    urgency_message: str                 # "Oferta válida esta semana"
    social_proof_message: str            # "Más de 500 alquileres realizados"
    
    # Quick benefits
    quick_benefits: List[BenefitDTO]     # [
                                         #   {"icon": "bi-truck", "label": "Transporte"},
                                         #   {"icon": "bi-wrench", "label": "Instalación"},
                                         # ]
    
    # Use cases
    use_cases: List[str]                 # ["Eventos", "Construcción", "Filmación"]
    
    # Comparativa compra vs alquiler
    purchase_price_reference: Decimal    # Precio de compra nuevo
    financial_message: str               # "Comprar es más caro a largo plazo"
    savings_vs_purchase: SavingsDTO      # {"savings_pct": 65, "message": "Ahorras 65% vs comprar"}
    
    # Promo banner
    promo_banner_message: str            # "Transporte incluido esta semana"
```

---

### 2.4 EquipmentTechnicalDTO

```python
@dataclass
class EquipmentTechnicalDTO:
    """Especificaciones técnicas.
    
    Features, Specs, Requirements.
    """
    # Características destacadas
    features: List[FeatureDTO]           # [
                                         #   {"title": "Potencia", "value": "20T", "icon": "..."},
                                         # ]
    
    # Especificaciones agrupadas
    specification_groups: List[SpecGroupDTO]  # [
                                              #   {
                                              #     "name": "Motor",
                                              #     "specs": [
                                              #       {"name": "Tipo", "value": "Diesel"},
                                              #       {"name": "Cilindrada", "value": "4L"},
                                              #     ]
                                              #   }
                                              # ]
    
    # Requisitos para rentar
    requirements: List[RequirementDTO]   # [
                                         #   {
                                         #     "title": "Acceso vehicular",
                                         #     "description": "Se requiere puerta de entrada de 3m"
                                         #   }
                                         # ]
```

---

### 2.5 EquipmentServicesDTO

```python
@dataclass
class EquipmentServicesDTO:
    """Servicios: incluidos vs opcionales.
    
    Diferenciación clara de alcance.
    """
    # Alcance del alquiler
    included_items: List[IncludedItemDTO]        # [
                                                  #   {
                                                  #     "title": "Cable de potencia",
                                                  #     "description": "Cable de 50m incluido",
                                                  #     "icon": "bi-plug"
                                                  #   }
                                                  # ]
    
    excluded_items: List[ExcludedItemDTO]        # [
                                                  #   {
                                                  #     "title": "Operador",
                                                  #     "description": "Se cobra por separado",
                                                  #     "icon": "bi-person"
                                                  #   }
                                                  # ]
    
    # Servicios adicionales (costo extra)
    optional_services: List[OptionalServiceDTO]  # [
                                                  #   {
                                                  #     "title": "Operador especializado",
                                                  #     "description": "Profesional para operar el equipo",
                                                  #     "price": 150000,
                                                  #     "formatted_price": "$150.000",
                                                  #     "icon": "bi-person-check"
                                                  #   }
                                                  # ]
    
    # Servicios incluidos en precio
    services_included: List[ServiceDTO]          # [
                                                  #   {
                                                  #     "title": "Transporte básico",
                                                  #     "description": "Entrega en Bogotá",
                                                  #     "icon": "bi-truck"
                                                  #   }
                                                  # ]
```

---

### 2.6 EquipmentMediaDTO

```python
@dataclass
class EquipmentMediaDTO:
    """Videos, documentos, imágenes.
    
    Contenido multimedia rico.
    """
    # Galería de imágenes (organizada por tipo)
    gallery: GalleryDTO                  # {
                                         #   "principal": ImageDTO,
                                         #   "principal_images": [ImageDTO, ...],
                                         #   "installation_images": [ImageDTO, ...],
                                         #   "details_images": [ImageDTO, ...],
                                         #   "view_360_images": [ImageDTO, ...],
                                         # }
    
    # Videos
    videos: List[VideoDTO]               # [
                                         #   {
                                         #     "title": "Cómo instalar",
                                         #     "type": "youtube",
                                         #     "url": "https://youtube.com/...",
                                         #     "thumbnail": "https://...",
                                         #   }
                                         # ]
    
    # Documentos descargables
    documents: List[DocumentDTO]         # [
                                         #   {
                                         #     "title": "Manual de operación",
                                         #     "type": "manual",
                                         #     "url": "https://...",
                                         #     "download_count": 42,
                                         #   }
                                         # ]
```

---

### 2.7 EquipmentPublicDetailDTO (DTO Unificado Principal)

```python
@dataclass
class EquipmentPublicDetailDTO:
    """DTO único que agrupa TODA la información pública.
    
    Reemplaza múltiples requests/parsing en frontend.
    """
    # Identidad
    uuid: str
    slug: str
    
    # Sections (DTOs anteriores)
    hero: EquipmentHeroDTO
    pricing: EquipmentPricingDTO        # Included en hero también
    marketing: EquipmentMarketingDTO
    technical: EquipmentTechnicalDTO
    services: EquipmentServicesDTO
    media: EquipmentMediaDTO
    
    # FAQ
    faqs: List[FAQDTO]                   # [
                                         #   {
                                         #     "question": "¿Qué incluye?",
                                         #     "answer": "...",
                                         #   }
                                         # ]
    
    # Reviews
    reviews: ReviewsDTO                  # {
                                         #   "average_rating": 4.5,
                                         #   "total_count": 42,
                                         #   "breakdown": {3: 2, 4: 10, 5: 30},
                                         #   "items": [ReviewDTO, ...],
                                         # }
    
    # Availability
    availability: AvailabilityDTO        # {
                                         #   "status": "available",
                                         #   "total_stock": 5,
                                         #   "available_now": 3,
                                         #   "next_available_date": "2026-08-05",
                                         # }
    
    # Commercial modalities
    commercial_options: List[CommercialOptionDTO]  # [
                                                    #   {
                                                    #     "modality": "renting",
                                                    #     "enabled": true,
                                                    #   },
                                                    #   {
                                                    #     "modality": "comodato",
                                                    #     "enabled": true,
                                                    #     "terms": [6, 12, 18, 24, 36],
                                                    #   }
                                                    # ]
    
    # Logistics (costos)
    logistics: LogisticsDTO              # {
                                         #   "delivery_cost": 150000,
                                         #   "pickup_cost": 100000,
                                         #   "formatted_delivery": "$150.000",
                                         #   "formatted_pickup": "$100.000",
                                         # }
    
    # Related equipment
    related_equipment: List[EquipmentPreviewDTO]  # [
                                                   #   {
                                                   #     "uuid": "...",
                                                   #     "name": "...",
                                                   #     "image": "...",
                                                   #     "price": "$...",
                                                   #   }
                                                   # ]
    
    # SEO
    seo: SEODTO                          # {
                                         #   "title": "...",
                                         #   "description": "...",
                                         #   "keywords": "...",
                                         #   "og_image": "...",
                                         # }
```

---

## 3. PRESENTERS EN BACKEND

### 3.1 EquipmentPricingPresenter

**Ubicación:** `renting/services/presenters.py`

```python
class EquipmentPricingPresenter:
    """Presenta pricing de equipo de forma comercial.
    
    Centraliza TODOS los cálculos de precio.
    Frontend nunca calcula nada.
    """
    
    def __init__(self, variant, marketing=None, cost_rules=None):
        self.variant = variant
        self.marketing = marketing or {}
        self.cost_rules = cost_rules or []
    
    def present(self) -> EquipmentPricingDTO:
        """Retorna DTO lista para renderizar."""
        price = self.variant.rental_price_per_day or 0
        promo = self.marketing.get('promo_price') or price
        reference = self.marketing.get('reference_price') or price
        
        # Aplicar cost rules (IVA, descuentos, etc)
        total = self._apply_cost_rules(price)
        
        return EquipmentPricingDTO(
            price_per_day=self.variant.rental_price_per_day,
            price_per_hour=self.variant.rental_price_per_hour,
            formatted_price_per_day=self._format_currency(price),
            formatted_price_per_hour=self._format_currency(self.variant.rental_price_per_hour or 0),
            reference_price=reference,
            promo_price=promo,
            formatted_reference_price=self._format_currency(reference),
            formatted_promo_price=self._format_currency(promo),
            discount_percentage=self._calculate_discount_pct(reference, promo),
            discount_amount=reference - promo if reference > promo else 0,
            formatted_discount_amount=self._format_currency(reference - promo if reference > promo else 0),
            has_promotion=(promo < reference),
            saving_message=f"Ahorras {self._format_currency(reference - promo)}",
            components=self._build_components(price, total),
            currency_code="COP",
            currency_symbol="$",
        )
    
    def _apply_cost_rules(self, base_price):
        """Aplica IVA, descuentos, recargos."""
        total = base_price
        for rule in self.cost_rules:
            if rule.applies_to_variant(self.variant):
                total += rule.calculate_amount(base_price)
        return total
    
    def _format_currency(self, amount: Decimal) -> str:
        """Formatea moneda colombiana: "$2.950.000" """
        # Implementación
        pass
    
    def _calculate_discount_pct(self, ref, promo) -> int:
        """Calcula porcentaje de descuento."""
        if not ref or ref == 0:
            return 0
        return int((ref - promo) / ref * 100)
    
    def _build_components(self, base, total) -> List[Dict]:
        """Arma desglose de costos."""
        # Retorna [
        #   {"label": "Precio base", "amount": "$..."},
        #   {"label": "IVA 19%", "amount": "$..."},
        #   {"label": "TOTAL", "amount": "$...", "bold": True},
        # ]
        pass
```

---

### 3.2 EquipmentPublicDetailPresenter

**Ubicación:** `renting/services/presenters.py`

```python
class EquipmentPublicDetailPresenter:
    """Presenta un equipo completo para detalle público.
    
    Orquesta todos los DTOs anteriores en uno solo.
    Llamado desde endpoint GET /equipment/{uuid}/detail/
    """
    
    def __init__(self, equipment, user=None):
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
    
    def _present_hero(self, variant) -> EquipmentHeroDTO:
        """Presenta hero section."""
        # Lógica
        pass
    
    def _present_pricing(self, variant) -> EquipmentPricingDTO:
        """Usa EquipmentPricingPresenter."""
        marketing = self.equipment.marketing or {}
        cost_rules = self.equipment.cost_rules.all()
        presenter = EquipmentPricingPresenter(variant, marketing, cost_rules)
        return presenter.present()
    
    def _present_marketing(self) -> EquipmentMarketingDTO:
        """Presenta marketing info."""
        marketing = self.equipment.marketing or {}
        tags = self._resolve_tags(marketing.get('tags', []))
        return EquipmentMarketingDTO(
            tags=tags,
            featured_benefit=marketing.get('featured_benefit', ''),
            main_message=marketing.get('main_message', ''),
            trust_message=marketing.get('trust_message', ''),
            urgency_message=marketing.get('urgency_message', ''),
            social_proof_message=marketing.get('social_proof_message', ''),
            quick_benefits=marketing.get('quick_benefits', []),
            use_cases=marketing.get('use_cases', []),
            purchase_price_reference=marketing.get('purchase_price_reference'),
            financial_message=marketing.get('financial_message', ''),
            savings_vs_purchase=self._calculate_savings(marketing),
            promo_banner_message=marketing.get('promo_banner_message', ''),
        )
    
    def _present_technical(self) -> EquipmentTechnicalDTO:
        """Presenta especificaciones técnicas."""
        return EquipmentTechnicalDTO(
            features=[
                FeatureDTO(
                    title=f.title,
                    value=f.value,
                    icon=f.icon,
                )
                for f in self.equipment.features.filter(is_active=True)
            ],
            specification_groups=[
                SpecGroupDTO(
                    name=group.name,
                    specs=[
                        {"name": s.name, "value": s.value}
                        for s in group.specifications.filter(is_active=True)
                    ],
                )
                for group in self.equipment.specification_groups.filter(is_active=True)
            ],
            requirements=[
                RequirementDTO(
                    title=r.title,
                    description=r.description,
                )
                for r in self.equipment.requirements.filter(is_active=True)
            ],
        )
    
    def _present_services(self) -> EquipmentServicesDTO:
        """Presenta servicios incluidos/opcionales."""
        # Lógica
        pass
    
    # ... resto de métodos
```

---

## 4. ÁRBOL DE COMPONENTES FRONTEND

### 4.1 Estructura Jerárquica

```
EquipmentDetailPage.vue (Orquestador)
│
├── EquipmentHeroSection
│   ├── HeroGallery (async)
│   ├── HeroPricing
│   ├── HeroMarketing
│   ├── HeroCTA
│   └── HeroTrustIndicators
│
├── EquipmentMarketingBand (si no está en hero)
│   ├── TagBadges
│   ├── BenefitBand
│   ├── UrgencyBanner
│   └── SocialProof
│
├── EquipmentTechnicalSection (tabs o accordion)
│   ├── EquipmentFeatureGrid (async)
│   ├── EquipmentSpecificationTable (async)
│   └── EquipmentRequirementsGrid (async)
│
├── EquipmentServicesSection (tabs)
│   ├── IncludedItemsGrid
│   ├── ExcludedItemsGrid
│   └── OptionalServicesGrid (async)
│
├── EquipmentMediaSection (tabs)
│   ├── VideosGallery (async)
│   ├── DocumentsTable (async)
│   └── DetailedGallery (async)
│
├── EquipmentComparativeBand (si existe purchase_price)
│   └── PricingComparison
│
├── EquipmentFAQSection (accordion, async)
│   └── FAQAccordion
│
├── EquipmentReviewsSection (async)
│   ├── ReviewsSummary
│   └── ReviewsList
│
├── CommercialModalitySelector (si hay Comodato)
│   ├── RentingOption
│   └── ComodatoOption
│
└── RelatedEquipmentSection (async)
    └── EquipmentCarousel
```

---

### 4.2 Componentes Reutilizables (Enterprise)

```
components/
└── marketplace/
    ├── ProductHero/                     (Reutilizable Shop/Services/Renting)
    │   ├── ProductHeroGallery.vue
    │   ├── ProductHeroPricing.vue
    │   ├── ProductHeroMarketing.vue
    │   └── ProductHeroCTA.vue
    │
    ├── ProductFeatures/                 (Reutilizable)
    │   ├── FeatureGrid.vue
    │   ├── FeatureTable.vue
    │   └── FeatureCard.vue
    │
    ├── ProductServices/                 (Reutilizable)
    │   ├── IncludedItemsList.vue
    │   ├── ExcludedItemsList.vue
    │   └── OptionalServicesGrid.vue
    │
    ├── ProductMedia/                    (Reutilizable)
    │   ├── MediaGallery.vue
    │   ├── VideoGallery.vue
    │   └── DocumentsTable.vue
    │
    ├── ProductFAQ/                      (Reutilizable)
    │   └── FAQAccordion.vue
    │
    ├── ProductReviews/                  (Reutilizable)
    │   ├── ReviewsSummary.vue
    │   └── ReviewsList.vue
    │
    └── ProductComparison/               (Reutilizable)
        └── PricingComparison.vue

modules/
└── renting/
    ├── RentalDetailPage.vue             (Orquestador específico de renting)
    ├── RentalDetailView.vue             (Wrapper de página)
    │
    └── sections/
        ├── RentalAvailabilityBand.vue
        ├── RentalCommercialOptions.vue
        ├── RentalLogisticsCosts.vue
        └── RentalRequirements.vue

stores/
└── rentingDetail.js                     (Pinia store para detail page)
```

---

## 5. FLUJO DE DATOS FRONTEND

### 5.1 Actual (Fragmentado)

```
RentalDetailView.vue
│
├── fetch equipment (GET /equipment/{uuid}/)
├── fetch marketing (si no está en equipment)
├── fetch reviews (si no está en equipment)
├── fetch availability (GET /equipment/{uuid}/availability/)
│
└── Local computation:
    ├── priceSummary() ← Frontend calcula
    ├── discount_percentage ← Frontend calcula
    ├── availabilityLabel ← Frontend calcula
    └── reviewSummary ← Frontend calcula
```

### 5.2 Nuevo (Unificado)

```
RentalDetailPage.vue
│
├── Single fetch (GET /equipment/{uuid}/detail/)
│   └── EquipmentPublicDetailDTO
│       ├── hero (todo listo)
│       ├── pricing (todo calculado)
│       ├── marketing (todo formateado)
│       ├── technical (todo organizado)
│       ├── services (todo desglosado)
│       ├── media (todo indexado)
│       ├── faqs (todo pagado)
│       ├── reviews (summary + items)
│       ├── availability (timeline)
│       ├── commercial_options (modalidades)
│       ├── logistics (costos)
│       ├── related_equipment (recomendaciones)
│       └── seo (metadata)
│
└── Only render:
    ├── HeroSection (datos ya listos)
    ├── MarketingSection (datos ya listos)
    ├── TechnicalSection (datos ya listos)
    ├── ServicesSection (datos ya listos)
    ├── MediaSection (datos ya listos)
    ├── ComparisonSection (datos ya listos)
    ├── FAQSection (datos ya listos)
    ├── ReviewsSection (datos ya listos)
    ├── CommercialOptions (datos ya listos)
    └── RelatedSection (datos ya listos)
```

---

## 6. ENDPOINT NUEVO (SIN BREAKING CHANGES)

### 6.1 GET /api/v1/equipment/{uuid}/detail/

```python
# renting/api/views.py
class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    # ... existing code ...
    
    @action(detail=True, methods=['get'])
    def detail(self, request, uuid=None):
        """GET /equipment/{uuid}/detail/
        
        Retorna EquipmentPublicDetailDTO con toda la información
        lista para renderizar una página de detalle enterprise.
        
        No rompe API existente:
        - GET /equipment/{uuid}/ sigue funcionando igual
        - Este es un endpoint NUEVO que agrupa información
        """
        equipment = self.get_object()
        presenter = EquipmentPublicDetailPresenter(equipment, user=request.user)
        dto = presenter.present()
        
        serializer = EquipmentPublicDetailDTOSerializer(dto)
        return Response(serializer.data)
```

---

## 7. VALIDACIÓN DE NO-BREAKING-CHANGES

### 7.1 Checklist

- ✓ Endpoint actual (`/equipment/{uuid}/`) NO se modifica
- ✓ Serializers actuales NO se tocan
- ✓ Modelos NO se tocan
- ✓ Permisos NO se tocan
- ✓ Frontend puede elegir qué endpoint usar
- ✓ Fallback a viejo parser si `/detail/` no existe

### 7.2 Migración en Frontend

```javascript
// RentalDetailView.vue (nuevo)
async function loadEquipmentDetail(uuid) {
  try {
    // Intentar el nuevo endpoint
    const { data } = await api.get(`/equipment/${uuid}/detail/`);
    return data;  // EquipmentPublicDetailDTO
  } catch {
    // Fallback al viejo endpoint + parsing manual
    const equipment = await api.get(`/equipment/${uuid}/`);
    return parseOldFormat(equipment);
  }
}
```

---

## 8. IMPACTO EN BACKEND

### 8.1 Archivos a Crear

```
renting/services/
├── presenters.py          [NUEVO] (300+ líneas)
│   ├── EquipmentPricingPresenter
│   └── EquipmentPublicDetailPresenter
│
└── dtos.py                [NUEVO] (200+ líneas)
    └── Todas las DTOs (dataclasses)

renting/api/
├── equipment_serializers.py  [NUEVO] (150+ líneas)
│   └── EquipmentPublicDetailDTOSerializer
│
└── views.py               [MODIFICADO] (+30 líneas)
    └── Agregar @action detail()
```

### 8.2 Archivos a Modificar

```
renting/api/views.py       [+30 líneas] (agregar detail action)
renting/api/urls.py        [SIN CAMBIOS] (mantiene routing existente)
renting/models.py          [SIN CAMBIOS]
```

---

## 9. IMPACTO EN FRONTEND

### 9.1 Archivos a Crear

```
src/components/marketplace/      [NUEVOS] (reutilizables)
├── ProductHero/
│   ├── ProductHeroGallery.vue
│   ├── ProductHeroPricing.vue
│   ├── ProductHeroMarketing.vue
│   └── ProductHeroCTA.vue
│
├── ProductFeatures/
│   ├── FeatureGrid.vue
│   └── FeatureTable.vue
│
├── ProductServices/
│   ├── IncludedItemsList.vue
│   ├── ExcludedItemsList.vue
│   └── OptionalServicesGrid.vue
│
├── ProductMedia/
│   ├── MediaGallery.vue
│   ├── VideoGallery.vue
│   └── DocumentsTable.vue
│
├── ProductFAQ/
│   └── FAQAccordion.vue
│
├── ProductReviews/
│   ├── ReviewsSummary.vue
│   └── ReviewsList.vue
│
└── ProductComparison/
    └── PricingComparison.vue

src/modules/renting/         [NUEVOS] (específicos renting)
├── sections/
│   ├── RentalAvailabilityBand.vue
│   ├── RentalCommercialOptions.vue
│   ├── RentalLogisticsCosts.vue
│   └── RentalRequirements.vue

src/stores/
└── rentingDetail.js         [NUEVO] (Pinia store)

src/composables/
└── useEquipmentDetail.js    [NUEVO] (Fetch logic)
```

### 9.2 Archivos a Modificar

```
src/views/customer/renting/RentalDetailView.vue
└── [REEMPLAZAR] con versión nueva que usa EquipmentPublicDetailDTO

src/components/layout/BaseGallery.vue
└── [OPCIONAL] agregar filtrado por image_type
```

---

## 10. DIAGRAMA DE TRANSFORMACIÓN

```
Backend:                           Frontend:
────────                           ────────

Equipment ┐
Marketing ├─→ EquipmentPricingPresenter ──→ EquipmentPricingDTO ──→ HeroPricing
Variants  ┘                                                           ├─ Formatted prices
                                                                     ├─ Discount %
                                                                     └─ Savings message

Equipment ┐
Marketing ├─→ EquipmentMarketingPresenter ──→ EquipmentMarketingDTO ──→ HeroMarketing
Features  ┘                                                             ├─ Tags
                                                                       ├─ Messages
                                                                       └─ Benefits

EquipmentImage ─→ EquipmentMediaPresenter ──→ EquipmentMediaDTO ──→ MediaSection
RentalVideo ┘                                                       ├─ Gallery
RentalDocument                                                      ├─ Videos
                                                                    └─ Documents

RentalSpecification ┐
RentalFeature      ├─→ EquipmentTechnicalPresenter ──→ EquipmentTechnicalDTO ──→ TechnicalSection
RentalRequirement  ┘                                                           ├─ Features
                                                                              ├─ Specs
                                                                              └─ Requirements

[12 nested models] ──→ EquipmentPublicDetailPresenter ──→ EquipmentPublicDetailDTO ──→ RentalDetailPage

                      └──────────────────────────────────────────────────────┘
                              Single Unified DTO with all data ready to render
```

---

## 11. PRÓXIMOS PASOS

**Fase 2 DISEÑO:** ✓ COMPLETADO

Esta documentación define:
- ✓ DTOs (Backend)
- ✓ Presenters (Backend)
- ✓ Componentes (Frontend)
- ✓ Árbol de componentes
- ✓ Flujo de datos
- ✓ Endpoint nuevo
- ✓ Sin breaking changes

**Fase 3:** [IMPLEMENTACIÓN BACKEND]
- Crear `renting/services/presenters.py`
- Crear `renting/services/dtos.py`
- Crear endpoint `/detail/`
- Tests

**Fase 4:** [IMPLEMENTACIÓN FRONTEND]
- Crear componentes reutilizables
- Implementar RentalDetailPage nueva
- Integrar con Pinia store
- Tests

**Fase 5:** [HERO COMERCIAL]
- Pricing prominente
- Tags visibles
- CTA personalizable

...y así sucesivamente.

---

**Arquitectura validada contra:** ARQUITECTURA_COMPLETA_RENTIG.md  
**Status:** Listo para Fase 3 (Implementación Backend)
