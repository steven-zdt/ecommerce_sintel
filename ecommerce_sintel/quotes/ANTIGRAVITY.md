# App: quotes — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/quotes/.AGENT/docs/ARQUITECTURA_COMPLETA_QUOTES.md
```

## Responsabilidad de esta app

Generación de cotizaciones (presupuestos) para clientes, incluyendo productos,
servicios técnicos con materiales, y exportación a PDF.
Soporta cotizaciones anónimas (sin usuario registrado).

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Quotation, QuotationItem, QuotationService, QuotationMaterial, QuoteProduct, QuoteProductVariant |
| `api/views.py` | QuotationViewSet: create(), download_pdf() |
| `api/serializers.py` | QuotationSerializer, QuotationItemSerializer, QuotationServiceSerializer |
| `services/commands.py` | QuotationBuilder: create_quotation() |
| `services/pdf_service.py` | PDFService: generate_quotation_pdf() (ReportLab) |

## Patrones obligatorios en esta app

- **Snapshot completo:** Al crear, capturar `unit_price`, `labor_cost`, `unit_price` de materiales — los datos del presupuesto deben ser inmutables
- `QuotationBuilder.create_quotation()` usa `@transaction.atomic`: crea Quotation + todos los ítems y calcula subtotales
- **Cotización anónima:** `Quotation.user` es nullable — no asumir usuario autenticado
- Estados: `DRAFT → SENT → ACCEPTED / REJECTED / EXPIRED`
- PDF con ReportLab: tabla de productos + tabla de servicios con materiales nested
- `QuoteProduct`/`QuoteProductVariant` son productos "custom" creados solo para presupuestos (no del catálogo Shop)

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
