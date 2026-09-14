# Action Graph — Renting

Fecha de análisis: 2026-08-05. Fuente: `renting/models.py` previa a su extracción y contratos de la capa de aplicación.

## Agregados y relaciones

```text
Equipment
├── EquipmentVariant
│   ├── RentalRequest
│   │   ├── RentalRequestLocation
│   │   ├── RentalRequestContact
│   │   ├── RentalRequestCosts
│   │   ├── RentalRequestPaymentInfo
│   │   ├── RentalProjectAttachment
│   │   ├── RentalPeriod
│   │   ├── RentalOperation ── RentalOperationEvent
│   │   └── EquipmentReturnInspection ── EquipmentBlock (opcional)
│   ├── EquipmentBlock
│   └── RentalCostAssignment ── RentalCostRule
├── EquipmentImage
├── EquipmentReview
├── EquipmentLogisticsConfig
├── EquipmentCommercialConfig
├── EquipmentCommercialOption
├── EquipmentMarketing
└── Catálogo enriquecido
    ├── RentalIncludedItem / RentalExcludedItem / RentalFeature
    ├── RentalRequirement / RentalServiceIncluded / RentalOptionalService / RentalFAQ
    ├── RentalSpecificationGroup ── RentalSpecification
    └── RentalVideo / RentalDocument

RentingCategory ── Equipment ── RentingBrand
RentalLabor ── RentalRequest (M2M)
```

## Clasificación

| Grupo | Modelos | Clasificación | Razón |
|---|---|---|---|
| Equipo e inventario | `Equipment`, variante, imágenes, reseñas, categoría, marca | CORE | Fuente de catálogo, precio e inventario físico. |
| Solicitud y datos satélite | `RentalRequest` y cinco hijos | CORE | Ciclo contractual y compatibilidad de datos persistidos. |
| Agenda | `RentalPeriod`, `EquipmentBlock` | CORE | Fuente autónoma de disponibilidad. |
| Operación y retorno | operación, evento, inspección | CORE | Ejecución y trazabilidad postpago. |
| Configuración por equipo | logística, comercial, opciones, marketing | CONFIG | Datos administrables que modifican presentación u oferta, no el agregado base. |
| Catálogo enriquecido | 11 hijos de equipo | CATÁLOGO | Contenido descriptivo ordenado y administrable. |
| Costos y mano de obra | regla, asignación, labor | CONFIG | Pricing y datos de soporte reutilizables. |

## Dependencias de la aplicación

- Escritura: `services/commands.py`, `services/catalog.py`, `services/operations.py` y `services/pricing.py`.
- Lectura: `services/selectors.py`, `availability.py`, `summary.py`, `presenters.py` y `display.py`.
- Contratos HTTP: serializers, viewsets de Renting, operación y catálogo administrativo.
- Consumidores externos: Orders referencia `EquipmentVariant`; Payment y dashboard usan solicitudes y variantes; operaciones usa `DispatcherProfile` mediante una referencia diferida.

La extracción no cambia ninguno de estos símbolos: todos continúan importables mediante `from renting.models import ...`.
