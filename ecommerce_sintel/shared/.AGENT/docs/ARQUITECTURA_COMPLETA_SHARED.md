# App: shared — Arquitectura Completa

**Propósito:** DTOs, Presenters, Serializers compartidos entre módulos públicos.

**Fecha de creación:** 2026-07-29  
**Responsable:** UPDP (Unified Public Detail Platform)

---

## Resumen

App `shared` centraliza la lógica de presentación (DTOs + Presenters) para las páginas de detalle pública de los tres módulos:
- Renting (`/alquiler/equipo/{uuid}`)
- Shop (`/tienda/producto/{uuid}`)
- Technical Services (`/servicios/{uuid}`)

**Principio:** Toda transformación de datos vive en backend. Frontend solo renderiza.

---

## Estructura de Directorios

```
shared/
├── __init__.py
├── apps.py                    # Configuración de la app Django
├── .AGENT/
│   └── docs/
│       └── ARQUITECTURA_COMPLETA_SHARED.md  (este archivo)
├── dtos/
│   ├── __init__.py
│   └── public_detail.py       # UnifiedPublicDetailDTO (dataclasses)
├── presenters/
│   ├── __init__.py
│   └── public_detail.py       # PublicDetailPresenterBase + 3 implementations
├── serializers/
│   ├── __init__.py
│   └── public_detail.py       # UnifiedPublicDetailDTOSerializer
├── api/
│   ├── __init__.py
│   ├── urls.py                # /api/v1/unified/detail/<uuid>/
│   └── views.py               # UnifiedPublicDetailViewSet
└── tests/
    └── __init__.py            # Unit tests (TODO)
```

---

## DTOs (Data Transfer Objects)

### `shared/dtos/public_detail.py`

Define `UnifiedPublicDetailDTO` — el DTO maestro que agrupa TODA la información pública.

**Sub-DTOs incluidos:**

```python
UnifiedPublicDetailDTO
├── uuid, slug, module_type
├── hero: HeroDTO
├── gallery: GalleryDTO
├── pricing: PricingDTO
├── marketing: MarketingDTO
├── availability: AvailabilityDTO
├── description: DescriptionDTO
├── technical: TechnicalDTO
├── included_items: List[IncludedItemDTO]
├── excluded_items: List[ExcludedItemDTO]
├── requirements: List[RequirementDTO]
├── faq: List[FAQItemDTO]
├── documents: List[DocumentDTO]
├── videos: List[VideoDTO]
├── reviews: ReviewsSummaryDTO
├── related_items: List[RelatedItemDTO]
├── recommendations: List[RecommendationDTO]
└── seo: SEODTO
```

**Principios:**
- Todas son `@dataclass` (serialización automática)
- Nombres en inglés (contrato uniforme)
- Tipos tipados (`Optional[T]`, `List[T]`)
- Backend garantiza 100% completo, frontend nunca calcula

---

## Presenters

### `shared/presenters/public_detail.py`

Define la interfaz base y las 3 implementaciones específicas.

#### Base Class

```python
class PublicDetailPresenterBase(ABC):
    def __init__(self, item, user=None):
        self.item = item
        self.user = user

    @abstractmethod
    def present(self) -> UnifiedPublicDetailDTO:
        raise NotImplementedError()
```

#### Implementaciones Específicas

1. **`RentingPublicDetailPresenter`**
   - Convierte `Equipment` → `UnifiedPublicDetailDTO`
   - Reutiliza `EquipmentPublicDetailPresenter` de `renting/services/presenters.py`
   - Normaliza campos a schema unificado

2. **`ShopPublicDetailPresenter`**
   - Convierte `Product` → `UnifiedPublicDetailDTO`
   - Extrae imágenes, variantes, reviews
   - TODO: Conectar con `ProductPresenter` cuando exista

3. **`ServicePublicDetailPresenter`**
   - Convierte `TechnicalService` → `UnifiedPublicDetailDTO`
   - Extrae imágenes, variantes, reviews
   - TODO: Conectar con `ServicePresenter` cuando exista

---

## Serializers

### `shared/serializers/public_detail.py`

`UnifiedPublicDetailDTOSerializer`:
- Convierte `UnifiedPublicDetailDTO` (dataclass) → JSON
- Utiliza `SerializerMethodField` para convertir sub-dataclasses
- No toca BD, es pure transformation

---

## API

### `shared/api/views.py`

`UnifiedPublicDetailViewSet`:
- `GET /api/v1/unified/detail/<uuid>/?module=renting|shop|service`
- Retorna `UnifiedPublicDetailDTO` serializado

**Lógica:**
1. Query param `module` + URL param `uuid`
2. Selecciona el presenter correcto
3. Presenta el item
4. Serializa a JSON
5. Responde

### `shared/api/urls.py`

```python
urlpatterns = [
    path('unified/detail/<str:pk>/', ...)  # Se agrega a ecommerce/urls.py
]
```

---

## Integración en `ecommerce/urls.py`

Agregar a las URLs raíz:

```python
from shared.api.urls import urlpatterns as shared_urls

urlpatterns = [
    path('api/v1/', include(shared_urls)),
    # ... resto de URLs
]
```

---

## Flujo de Datos

```
Frontend Request
    ↓
GET /api/v1/unified/detail/<uuid>/?module=renting
    ↓
UnifiedPublicDetailViewSet.retrieve()
    ↓
RentingSelector.get_by_uuid() / ProductSelector / ServiceSelector
    ↓
RentingPublicDetailPresenter / ShopPublicDetailPresenter / ServicePublicDetailPresenter
    ↓
present() → UnifiedPublicDetailDTO
    ↓
UnifiedPublicDetailDTOSerializer
    ↓
JSON Response
    ↓
Frontend (PublicDetailView.vue)
```

---

## Cambios Recientes

### 2026-07-29 - Creación inicial
- Creada app `shared` con estructura completa
- DTOs unificados (25 sub-DTOs)
- Presenters base + 3 implementaciones
- Endpoint `/api/v1/unified/detail/<uuid>/`
- Serializer para UnifiedPublicDetailDTO

**Archivos creados:**
- `shared/dtos/public_detail.py` (500+ líneas)
- `shared/presenters/public_detail.py` (300+ líneas)
- `shared/serializers/public_detail.py` (150+ líneas)
- `shared/api/views.py` (100+ líneas)
- `shared/api/urls.py` (20 líneas)
- `shared/apps.py`, `__init__.py`, etc.

**Estado:** ✅ Backend base completo, listo para testing

---

## TODO (Próximas Fases)

### Fase 2: Frontend
- [ ] Crear `PublicDetailView.vue` unificado
- [ ] Actualizar router (3 rutas → 1 vista)
- [ ] Reemplazar 3 detail views actuales

### Fase 3: Módulos Nuevos
- [ ] `PublicDetailReviews` component
- [ ] `PublicDetailRelated` component
- [ ] `PublicDetailRecommendations` component

### Fase 4: Testing
- [ ] Unit tests para presenters
- [ ] Integration tests para API
- [ ] E2E tests en frontend

### Refinamiento
- [ ] Performance optimization
- [ ] Accessibility audit (WCAG 2.2)
- [ ] Documentation completar

---

## Validación / Testing

```python
# Test unitario básico
from shared.presenters import RentingPublicDetailPresenter
from renting.models import Equipment

equipment = Equipment.objects.first()
presenter = RentingPublicDetailPresenter(equipment)
dto = presenter.present()

assert dto.uuid == str(equipment.uuid)
assert dto.module_type == "renting"
assert dto.hero is not None
```

---

## Dependencias

- Django 5.2
- Django REST Framework
- dataclasses (built-in Python 3.7+)
- renting, shop, technical_services (para selectors)

---

## Notas Arquitectónicas

1. **Enterprise Pattern:** Todo presenter hereda de base class → contrato claro
2. **Dataclass Pattern:** DTOs como dataclasses → serialización automática
3. **Selector Pattern:** Presenters usan Selectors, no QuerySets directos
4. **No queries en ViewSets:** ViewSet solo orquesta, no toca BD
5. **Reusabilidad:** 3 módulos, 1 DTO, 3 presenters → máxima reutilización

---

## Glossario

| Término | Significado |
|---------|-----------|
| DTO | Data Transfer Object (dataclass con solo datos) |
| Presenter | Transforma modelo → DTO (lógica de presentación) |
| Serializer | Transforma DTO → JSON (representación HTTP) |
| Selector | Lee de BD (patrón de acceso a datos) |
| module_type | "renting" \| "shop" \| "service" |

---

**Documento autorizado:** UPDP Phase 1 - Backend Base
