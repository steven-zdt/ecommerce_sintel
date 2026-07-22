# App: technical_services — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md
```

## Responsabilidad de esta app

Catálogo de servicios técnicos (instalación, mantenimiento, reparación).
Precios calculados dinámicamente según SMLV colombiano o precio fijo.
Los materiales referencian ProductVariant del módulo shop.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | ServiceCategory, ServiceLevel, ServiceConfiguration, TechnicalService, ServiceVariant, ServiceMaterial, ServiceImage, ServiceReview |
| `api/views.py` | TechnicalServiceViewSet (ReadOnly), ServiceCategoryViewSet, ServiceLevelViewSet |
| `api/serializers.py` | TechnicalServiceSerializer, ServiceVariantSerializer (con `calculated_price`), ServiceMaterialSerializer |
| `services/commands.py` | ServiceCommands: request_service() |
| `services/selectors.py` | ServiceSelector: get_variant_quotation() |
| `services/calculator.py` | LaborCostCalculator: calculate_hourly_rate(), calculate_variant_labor_cost() |
| `services/summary.py` | ServicesSummaryProvider: get_summary() → stats para marketing |

## Patrones obligatorios en esta app

- **Precio dinámico vs. fijo:** Si `ServiceVariant.fixed_price` existe, usar ese precio. Si no, calcular con `LaborCostCalculator`
- **Fórmula SMLV:** `hourly_rate = (SMLV × (1 + prestaciones%) + subsidio_transporte) / 240 × (1 + overhead%)`
- `ServiceMaterial` referencia `shop.ProductVariant` para precios de insumos — no duplicar datos
- `get_variant_quotation()` retorna dict con `labor_cost`, `material_cost`, `total_price`, `breakdown`
- Notificar admin via WebSocket al crear solicitud de servicio: `group="admin_notifications"`
- `ServicesSummaryProvider.get_summary()` es consumido por marketing — mantener la firma del dict

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
