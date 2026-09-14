# WHITE_LABEL_MODULE_AUDIT.md
Fase 6, 7, 15, 23 — Auditoría del dashboard y scoring de módulos

Solo lectura.

> **CORRECCIÓN (2026-08-14):** el veredicto de Parte A de abajo decía que no existía UI de
> panel para `organization`. Es incorrecto — `/panel/organizacion` ya existe. Ver la nota de
> corrección completa en [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md).
> La tabla de la Parte A sigue siendo válida (esas secciones sí viven en `dashboard`); lo que
> cambia es que `organization` no necesitaba "F8: construir `/panel/organizacion`" porque ya
> existía — el trabajo real de F2 fue solo limpiar 2 accesos directos residuales.

## Parte A — Dashboard (BFF de administración)

`ecommerce_sintel/dashboard/` es un BFF puro (`dashboard/models.py` vacío) — cada `ViewSet` en `dashboard/api/urls.py` delega a un Orchestrator (`dashboard/services/admin_orchestrators.py`) que llama Commands/Selectors de la app dueña de los datos.

| Sección del panel | Clasificación | Evidencia |
|---|---|---|
| `products/`, `categories/`, `brands/`, `taxes/`, `shop-cost-rules/` (+ 13 subrecursos) | BUSINESS_CONFIGURATION | Catálogo/pricing de tienda |
| `equipment/`, `renting-*`, `rental-*` (12 subrecursos), `rental-cost-rules/` | BUSINESS_CONFIGURATION | Catálogo/pricing de renting |
| `service-packages/`, `services/`, `service-categories/`, `service-levels/`, `service-variants/`, `service-cost-rules/` (+10 subrecursos) | BUSINESS_CONFIGURATION | Catálogo/pricing de servicios |
| `quotations/`, `quote-template-*` (constructor de cuestionarios) | BUSINESS_CONFIGURATION | Estructura de cuestionario totalmente admin-configurable |
| `marketing/` | BUSINESS_CONFIGURATION | Ofertas sobre cualquiera de los 3 catálogos |
| `home-config/`, `home-cards/`, `feature-banner-*`, `footer/`, `site-brand/`, `navbar/`, `footer-cta/`, `brand-slider/`, `about-us/` | BUSINESS_CONFIGURATION | Superficie CMS principal de landing |
| `seo/meta-tags/`, `seo/verification-files/` | BUSINESS_CONFIGURATION | CMS de meta tags por página |
| `technical-services/requests/`, `orders/` | PLATFORM_ADMINISTRATION | Flujo operativo, no identidad |
| `payment-transactions/` | PLATFORM_ADMINISTRATION | Conciliación técnica |
| `operations/`, `dispatchers/`, `security-events/` | PLATFORM_ADMINISTRATION | Logística/auditoría |
| `notification-templates/` (contenido) / `notification-logs/` (logs) | Mixto — contenido=BUSINESS_CONFIGURATION, logs=PLATFORM_ADMINISTRATION | Plantillas editables por slug en DB |
| `support/chats/`, `ai-providers/`, `ai-channel-config/`, `metrics/` | PLATFORM_ADMINISTRATION | Moderación/técnico |

**Veredicto A:** No existe ninguna sección de panel para identidad institucional (nombre de empresa, datos legales, contacto, dominios, defaults SEO, redes sociales) — esos datos viven en `organization` (ver [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md)), que **es la SSoT correcta pero no está cableada al patrón BFF del dashboard**: está montada directamente en `/api/v1/organization/`, sin uso desde el frontend (`grep` de "organization" en `frontend/src` no arroja nada), y la propia app se marca "EN CONSTRUCCIÓN, Fase 3 de 9". **Recomendación: extender `organization` dentro del dashboard (construir `/panel/organizacion`), no crear un `/panel/business` paralelo** — el modelo de dominio ya existe y está bien separado, solo falta envolverlo con el orquestador estándar del dashboard y un módulo de frontend.

## Parte B — Scoring de acoplamiento por módulo (0=agnóstico, 4=crítico; total /32)

Ningún campo `choices=` de los 10 módulos hornea taxonomía del rubro seguridad (marcas de cámaras, tipos de alarma) — son enums genéricos de estado/tipo/prioridad. El contenido de catálogo (categorías, marcas, plantillas) vive en filas de DB, no en código, así que `data_coupling` es bajo en general. Menciones a "cámara/CCTV/alarma/vigilancia" en frontend son placeholders de formularios admin, no copy fijo — severidad baja. Referencias a "Sintel" en módulos son casi enteramente el nombre del componente compartido `SintelOffcanfas` (elección de naming, no fuga de marca) más un hostname Docker.

| Módulo | identity | content | pricing | workflow | route | UI | data | config-level (bajo=mejor) | **Total/32** |
|---|---|---|---|---|---|---|---|---|---|
| notifications | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | **1** |
| marketing | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | **2** |
| payment | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | **3** |
| orders | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | **3** |
| support | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | **3** |
| operations | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | **4** |
| shop | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | **6** |
| renting | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | **9** |
| technical_services | 1 | 2 | 1 | 2 | 2 | 1 | 1 | 1 | **11** |
| quotes | 1 | 2 | 2 | 3 | 2 | 2 | 1 | 1 | **14** |

**Notas de riesgo por módulo:**

- **notifications** — sin riesgo real; plantillas y canales son genéricos y editables en DB.
- **marketing** — importa `ProductVariant`/`ServiceVariant`/`EquipmentVariant` directamente, riesgo estructural (arquitectura), no de marca.
- **payment** — riesgo mayor: supuesto duro de Wompi-Colombia/COP horneado en modelos `Transaction`/`CODTransaction`, sin capa de proveedor de pago abstraída.
- **orders** — FSM genérica; riesgo menor por `driver_type`/métodos de envío que asumen flota propia.
- **support** — chat/CSAT genérico; riesgo por lógica de hand-off asumiendo la integración específica con `ai_engine`.
- **operations** — FSM de despacho genérica; riesgo leve de naming en comentarios/docs implicando despacho de técnicos de campo específicamente.
- **shop** — catálogo casi agnóstico; único riesgo es texto de ayuda ("Camara, Grabador" como ejemplo de especificaciones), fácil de cambiar.
- **renting** — FSM de renta genérica, pero `EquipmentImage.TYPE_INSTALLATION` y campos de costo de mano de obra asumen instalación física in-situ.
- **technical_services** — motor de pricing/calendario/timeline genérico, pero naming de paquetes ("Mantenimiento CCTV 8 Camaras") y lógica de altura/andamiaje (compartida con quotes) apuntan fuerte al vertical de instalación.
- **quotes** — el más acoplado: `quotes/services/labor_conditions_evaluator.py` (`LaborConditionsEvaluator`) hornea umbrales de riesgo de trabajo en altura y labels en español ("Andamio"/"Escalera") **directamente en código, sin configuración admin** — el único hallazgo genuino de `workflow_coupling` fuerte en todo el codebase (ver [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md)).

**Ranking, de más a menos listo para business-agnostic:**

1. notifications (1/32)
2. marketing (2/32)
3. payment / orders / support (3/32, empate — riesgos distintos)
4. operations (4/32)
5. shop (6/32)
6. renting (9/32)
7. technical_services (11/32)
8. quotes (14/32) — necesita externalizar/configurar el evaluador de condiciones laborales antes de blanquear fuera de negocios tipo instalación
