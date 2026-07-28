# App: quotes — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/quotes/.AGENT/docs/ARQUITECTURA_COMPLETA_QUOTES.md
```

## Responsabilidad de esta app

Dos flujos sobre el mismo modelo `Quotation` (ver ARQUITECTURA_COMPLETA_QUOTES.md
para el detalle completo):
1. **Catalogo/personalizado (legado):** el asesor arma una cotizacion con
   productos/servicios/alquileres con precio inmediato.
2. **Constructor de Cuestionarios Tecnicos (`/cotizar`, principal):** el
   cliente **autenticado** responde una plantilla (sin precios) y genera una
   Solicitud de Cotizacion; un asesor la revisa y cotiza despues.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Quotation, QuotationTimeline, QuotationItem/Service/Material (legado); QuoteTemplate, QuoteTemplateModule, QuoteQuestion, QuoteQuestionOption (cuestionario) |
| `api/views.py` | QuotationViewSet: create(), from_template(), send(), download_pdf() |
| `api/serializers.py` | QuotationSerializer (legado); QuotationFromTemplateInputSerializer, QuoteTemplateInputSerializer, QuoteQuestionInputSerializer (cuestionario) |
| `services/commands.py` | QuotationBuilder (legado); QuotationCommands.create_from_template()/mark_as_sent(); QuoteTemplateCommands, QuoteQuestionCommands |
| `services/pdf_service.py` | PDFService: generate_quotation_pdf() (ReportLab) |

## Patrones obligatorios en esta app

- **Snapshot completo:** Al crear, capturar `unit_price`, `labor_cost`, `unit_price` de materiales — los datos del presupuesto deben ser inmutables
- `QuotationBuilder.create_quotation()` usa `@transaction.atomic`: crea Quotation + todos los ítems y calcula subtotales
- **Flujo legado (`create()`):** `Quotation.user` es nullable — cotizacion anonima posible en este flujo, pero NO en `from-template`.
- **Flujo de cuestionario (`from-template`):** exige `IsAuthenticated` en el backend (defensa en profundidad, no solo guard de frontend) y `document_type`/`document_number` obligatorios — ninguna solicitud se crea sin destinatario identificado. `template` debe estar `is_published=True, is_active=True` (validado en el queryset del serializer).
- **Estados reales (10, en español):** `BORRADOR, RECIBIDA, EN_REVISION, PENDIENTE_INFORMACION, COTIZADA, ENVIADA, ACEPTADA, RECHAZADA, VENCIDA, CANCELADA` — ver `Quotation.STATUS_CHOICES`. Sin maquina de estados estricta (transiciones libres, decision de negocio).
- **Auditoria append-only:** todo cambio de estado (incluido `send()`) debe crear un `QuotationTimeline` con `changed_by`.
- PDF con ReportLab: rama "requerimiento" (sin items) o "cotizacion" (con items/servicios con precio)
- `QuoteProduct`/`QuoteProductVariant` son productos "custom" creados solo para presupuestos (no del catálogo Shop)

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
