# Informe Ejecutivo — Auditoría Arquitectónica Transversal Sintel ERP

**Fecha:** 2026-08-05 · **Alcance:** Core, Organization, Accounts, Payment, Shop, Renting,
Technical Services, Notifications, Quotes, Frontend · **Método:** documentación
`ARQUITECTURA_COMPLETA_*.md` de cada módulo como fuente única de verdad (convención ya
establecida del proyecto), con spot-checks contra código real donde un hallazgo lo ameritaba.
4 agentes de exploración en paralelo (Core+Organization, Accounts+Payment, Notifications+Quotes,
Renting) + auditoría directa de Shop/Technical Services/Frontend desde conocimiento verificado
en esta misma sesión (trabajo reciente, sin riesgo de doc obsoleta). Plan de seguimiento:
[`PLAN_AUDITORIA_TRANSVERSAL.md`](PLAN_AUDITORIA_TRANSVERSAL.md). Brief original:
[`auditori_responsabilidades_tranversal.md`](auditori_responsabilidades_tranversal.md).

**Resultado en una frase:** el sistema no tiene un problema de arquitectura de dominio (los
bounded contexts están, en general, bien trazados) — tiene un problema de **patrones repetidos
sin abstracción compartida** (mismo shape de modelo/servicio/endpoint reimplementado de forma
independiente 2-4 veces entre módulos hermanos) y un problema **documental sistémico** (los 10
módulos auditados mostraron desactualización o bloat de changelog, sin excepción).

---

## 1. Estado actual de la arquitectura

Django 5 + DRF, arquitectura por apps con Service Layer (Commands/Selectors) ya adoptado de forma
consistente en los 10 módulos — ningún módulo auditado accede a modelos directamente desde
vistas sin pasar por selector/command, salvo una excepción puntual documentada (`core/api/views.py
::enums()`, ver §6). `dashboard/` funciona como BFF administrativo centralizado: los 4 módulos de
catálogo (Shop/Renting/Technical Services, y Quotes para su propia administración) delegan su
CRUD de escritura ahí en vez de exponerlo en su propia API — **patrón consistente e intencional
en todo el proyecto**, confirmado en los 4 módulos, no una desviación aislada.

`shared/` (nuevo, construido en esta misma sesión) es la primera pieza de infraestructura
genuinamente genérica cross-módulo del proyecto (`ContentBlockConfig`/`CatalogRelation`,
identificados por `ContentType`+`uuid`, sin `GenericForeignKey`) — un precedente real de que la
generización cross-módulo es viable en este codebase sin romper nada (30+80 tests pasando entre
Shop y Technical Services tras generalizarlo).

## 2. Grafo completo del sistema (Fase 0)

```
organization  (hoja — solo depende de django.conf.settings; 0 fan-out de dominio)
    ▲
    ├── core            (contact/brand/social, vía OrganizationSelector)
    ├── notifications    (email sender, admin login URL)
    ├── marketing        (8 adaptadores de canal)
    ├── accounts/users   (fallbacks: frontend_base_url, DEFAULT_FROM_EMAIL)
    └── quotes           (branding de PDF, OrganizationSelector.get_company())

notifications  (máximo fan-in de dominio: ~13-18 apps invocan dispatch_notification)
    ▲── orders, payment, renting, technical_services, kyc, accounts, operations,
        support, quotes (2 bypasses documentados: PDF de quotes, OTP de users)

dashboard  (máximo fan-in de BFF admin — hub, no violación, patrón confirmado)
    ▲── shop, renting, technical_services, quotes, payment, core, organization, accounts

shop ◄──────────────┐
  │ (ServiceMaterial.product_variant)
  ▼                 │
technical_services ──┤
  │ (variant snapshots)
  ▼                 │
renting ─────────────┤
  │                  │
  ▼                  ▼
payment ──────► orders/renting (Transaction FK) ──► inventory (deducción de stock)
  │
  └──► technical_services, operations (fan-out post-pago: 5 dominios desde
        payment/shared/commands.py::confirm_order_payment(), chokepoint deliberado)

quotes ──► shop, technical_services, renting (snapshot de variantes)
       ──► organization (branding PDF)
       ──► dashboard (su propio CRUD admin vive ahí, no en quotes/services/)

shared ◄── shop, technical_services (ContentBlockConfig/CatalogRelation — genérico
            por diseño, listo para Renting sin cambios de modelo)

accounts ──► kyc, orders (lazy import), technical_services (M2M), operations
frontend ──► todos los backends via dashboard/ (escritura) + apps públicas (lectura)
```

**Nodo más limpio:** `organization` — cero dependencias de dominio, solo `django.conf.settings`,
fan-in amplio y unidireccional. Es el ejemplo a seguir del proyecto.
**Nodos de mayor fan-in:** `notifications` (event sink, débil/por diseño) y `dashboard` (BFF
admin, débil/por diseño) — ambos intencionales, no accidentales.
**Dependencia más fuerte/riesgosa:** `payment/shared/commands.py::confirm_order_payment()` — un
solo método coordina 5 dominios (inventory/services/operations/fulfillment/notifications). Alto
radio de impacto si falla, mitigado por ser un único chokepoint documentado (no disperso).
**Sin dependencias circulares confirmadas** en ninguno de los 10 módulos auditados.

## 3. Dependencias entre módulos (detalle Fase 7)

| Módulo | Depende de (necesaria) | Acoplamiento débil | Acoplamiento fuerte / riesgo |
|---|---|---|---|
| Organization | `django.conf.settings` | Todo | — |
| Core | organization, marketing, shop, renting, technical_services | selectors (mayoría) | `enums()` importa modelos de orders/technical_services/kyc directo, salteando selectors |
| Accounts | kyc, technical_services, operations | — | `orders` vía lazy-import para ShippingAddress (cross-domain bleed) |
| Payment | orders, renting, inventory, security, notifications | inventory (unidireccional confirmado) | fan-out a 5 dominios desde un chokepoint |
| Shop | inventory, users, shared, accounts | — | — |
| Renting | payment, orders, operations, notifications | — | — |
| Technical Services | shop, accounts, users, shared, orders | — | 30 modelos en 1 app (ver §6) |
| Notifications | — (sink puro) | contrato por slug string, no FK | — |
| Quotes | shop, technical_services, renting, organization, notifications, dashboard | — | admin CRUD vive fuera de quotes/ |

## 4. Problemas encontrados (resumen, evidencia completa en §5-6)

1. Mismo patrón de modelo/servicio reimplementado 2-4 veces entre módulos hermanos, sin
   abstracción compartida (Review, CostRule/CostAssignment, singleton-config, admin
   child-orchestrator, ContentBlock/Relation admin views, managers Vue de catálogo).
2. Documentación desactualizada o con bloat de changelog en **los 10 módulos**, sin excepción —
   el hallazgo más consistente de toda la auditoría.
3. `RentalRequest` (Renting): el modelo más grande y central del módulo está documentado como un
   modelo plano de ~50 campos; el código real lo normalizó en 4 tablas hijas hace varias
   migraciones, con una fachada de propiedades — la doc no refleja la arquitectura actual del
   modelo más importante del módulo.
4. Archivo residual `quotes/services/labor_conditions_evaluator.py` contradice la afirmación de
   la doc de que el motor de cálculo legado fue "eliminado por completo".
5. `technical_services` concentra 4 responsabilidades (catálogo/contenido, motor de precios,
   agenda de técnicos, FSM de operación) en una sola app Django de 30 modelos.
6. Archivos de servicio grandes que mezclan responsabilidades: `accounts/services/commands.py`
   (1176 líneas, 2 clases no relacionadas), `payment/online/api/views.py` (756 líneas, ViewSet +
   sync + HMAC), `quotes/services/commands.py` (747 líneas, 8 clases CRUD boilerplate no
   factorizadas con el patrón helper que sí usan Shop/Renting/Services).

## 5. Duplicaciones detectadas (con evidencia)

| Duplicación | Dónde | Evidencia |
|---|---|---|
| Modelo "Reseña" (user+rating+comment, `unique_together`) | `shop.ProductReview`, `renting.EquipmentReview`, `technical_services.ServiceReview`, `accounts.ContractorReview` | 4 modelos, mismo shape, verificado por los 3 agentes + conocimiento directo |
| Modelo "Regla de costo" (fijo/porcentaje, TAX/DISCOUNT/SETUP/OPERATIONAL) | `shop.ProductCostRule/Assignment`, `renting.RentalCostRule/Assignment`, `technical_services.ServiceCostRule/Assignment` | 6 modelos, mismo shape — la duplicación de modelo/servicio más clara de todo el audit |
| Patrón "singleton config, GET+upsert" reimplementado sin base compartida | `core.FooterCTAConfig`/`BrandSliderConfig`/`AboutUsConfig` (3x independiente); `payment.PaymentFeatureFlags` (autoconfesado en su propia doc, línea 253-255) | Contraste directo: `organization.SingletonMixin` ya resuelve esto bien para 7 modelos — el patrón correcto YA EXISTE en el proyecto, simplemente no se reutilizó |
| Orquestador admin de catálogo hijo (7 métodos estáticos, dispatch por registry) | `ProductCatalogChildOrchestrator`, `RentingCatalogChildOrchestrator`, `ServicePackageChildOrchestrator`, `ServiceCatalogChildOrchestrator` — las 4 en `dashboard/services/admin_orchestrators.py` | 4 clases estructuralmente idénticas, ninguna con base común, confirmado por el agente de Renting línea por línea |
| ViewSets admin de `ContentBlockConfig`/`CatalogRelation` | `AdminProductContentBlockViewSet`/`AdminServiceContentBlockViewSet`, `AdminProductRelationViewSet`/`AdminServiceRelationViewSet` (`dashboard/api/content_blocks_views.py`) | Autodetectado durante la construcción esta sesión — documentado explícitamente como decisión pendiente en el propio código |
| Managers admin Vue de catálogo (Specifications/Documents/Videos) | `modules/shop/catalog/*Manager.vue` vs `modules/technical_services/catalog/Service*Manager.vue` | 4 pares casi byte-idénticos, mismo origen que el punto anterior |
| Concepto "producto" modelado 2 veces dentro del mismo módulo | `quotes.QuoteProduct/QuoteProductVariant` (producto custom) vs `quotes.QuotationItem` (snapshot de `shop.ProductVariant` real) | Confirmado por agente de Notifications+Quotes |
| CRUD boilerplate sin factorizar (8 clases Command casi idénticas) | `quotes/services/commands.py:346-745` | Contraste con `shop/services/catalog.py`/`renting/services/catalog.py` (SÍ factorizados con helpers `_reorder`/`_toggle_active`/`_soft_delete`/`_duplicate`) |
| Familia de componentes `Equipment*.vue` (10 componentes) usada por 3 módulos bajo nombre de uno solo | `components/renting/detail/Equipment*` reusado por Shop y Technical Services | Deuda de nombre, no funcional — confirmado en las 2 campañas de implementación de esta sesión |
| Kill-switch de pagos duplicado en vez de compartido | `renting/api/views.py::process_payment()` replica lógica en vez de compartir con `payment` | Confirmado por agente de Accounts+Payment |
| 2 endpoints de polling casi idénticos sobre el mismo side-effect | `payment` `transaction-status/` vs `confirmation/` (ambos llaman `_sync_wompi_status()`) | Documentado como intencional por el propio doc de Payment, igual se lista como duplicación de superficie de API |

## 6. Responsabilidades incorrectas / mezcladas

- **`technical_services`** (hallazgo más significativo de responsabilidad mezclada): una sola app
  Django concentra catálogo/contenido (recién construido esta sesión), motor de precios SMLV,
  motor de disponibilidad de técnicos, y FSM completa de operación de servicio (10 estados) — 4
  bounded contexts, 30 modelos. La propia documentación de Renting confirma que ahí SÍ se separó
  deliberadamente el FSM operativo (`RentalOperation`) del resto como "dominio separado" — el
  mismo criterio no se aplicó en Technical Services.
- **`core`**: posee `AboutUsConfig`/`AboutUsValue` (filosofía institucional) una semana después de
  que `organization` se creara explícitamente como SSoT de "todo dato institucional/de empresa" —
  contradicción directa con el propósito de la migración que separó ambas apps.
- **`payment`**: es simultáneamente el SSoT de integridad transaccional Y el orquestador de
  efectos post-pago cross-dominio (inventario, servicios, operaciones, fulfillment,
  notificaciones) — documentado y defendible como chokepoint único, pero es la definición textual
  de "responsabilidad mezclada" que pide el brief, y vale la pena que quede nombrado
  explícitamente aunque no se toque.
- **`organization`**: `CommunicationEvent` (telemetría de interacciones del widget) vive en un
  módulo por lo demás 100% de configuración institucional — único modelo de escritura pública, no
  singleton, en una app diseñada para lo contrario. Auto-reconocido en su propia doc como
  "excepción deliberada" pero sin evaluar si `notifications` sería un hogar más natural.
- **`accounts`**: crea `ShippingAddress` (dominio de `orders`) durante el registro — un import
  cruzado perezoso que funciona pero es responsabilidad de otro módulo ejecutándose desde acá.
- **`quotes`**: su CRUD administrativo completo (no solo catálogo hijo, como en Shop/Renting/
  Services) vive en `dashboard/services/admin_orchestrators.py` en vez de `quotes/services/` —
  dado que el patrón "dashboard es el BFF admin" SÍ es consistente en todo el proyecto, esto no es
  una desviación real, pero conviene que quede documentado como el caso más extremo de esa
  convención (CRUD completo, no solo hijos de catálogo).

## 7. Código susceptible de eliminarse

- `quotes/services/labor_conditions_evaluator.py` — verificar si es remanente muerto del motor de
  cálculo que la doc afirma "eliminado por completo"; si no tiene caller activo, eliminar.
- Ningún otro código muerto nuevo detectado en Core/Organization/Accounts/Payment/Notifications/
  Renting en esta pasada (más allá de lo ya limpiado en Shop/Technical Services/Frontend durante
  esta misma sesión: `ProductTabs.vue`, `ServiceFeatureList/ScopeList/SpecificationTable.vue`,
  `ServiceDetailView.vue` huérfano — ya eliminados, no un pendiente).

## 8. Modelos fusionables (candidatos, ver Fase 12 antes de ejecutar cualquiera)

| Candidato | Modelos hoy | Diseño propuesto | Riesgo |
|---|---|---|---|
| Reseñas | `ProductReview`, `EquipmentReview`, `ServiceReview`, `ContractorReview` (4 tablas) | 1 modelo genérico `Review` (`content_type`+`object_uuid`, mismo patrón ya probado con `ContentBlockConfig`) | Medio — requiere migración de datos de 4 tablas a 1, y actualizar 4 serializers/endpoints públicos existentes (rompería contratos si no se hace con cuidado — ver Fase 12) |
| Reglas de costo | `ProductCostRule/Assignment`, `RentalCostRule/Assignment`, `ServiceCostRule/Assignment` (6 tablas) | Clase base abstracta compartida (`shared.models.AbstractCostRule`) — reduce código duplicado, mismo conteo de tablas (más seguro que unificar en 1 tabla porque cada motor de precios ya tiene lógica propia acoplada a su propio modelo) | Bajo si se hace solo a nivel de clase abstracta (sin migración de datos); alto si se intenta unificar en una sola tabla |
| Singleton-config sin patrón compartido | `core.FooterCTAConfig/BrandSliderConfig/AboutUsConfig`, `payment.PaymentFeatureFlags` | Adoptar `organization.SingletonMixin` (ya existe y ya funciona para 7 modelos) | Bajo — es adoptar un mixin ya probado, no inventar uno nuevo |

## 9. Servicios fusionables

- 4 orquestadores admin de catálogo hijo (`ProductCatalogChildOrchestrator`/
  `RentingCatalogChildOrchestrator`/`ServicePackageChildOrchestrator`/
  `ServiceCatalogChildOrchestrator`) → 1 clase genérica parametrizada por registry (mismo espíritu
  que ya se usa dentro de cada uno individualmente).
- 2 pares de ViewSets `ContentBlockConfig`/`CatalogRelation` (Shop/Services) → 1 ViewSet
  parametrizado por `module` (ya identificado como pendiente en el propio código de esta sesión).
- `accounts/services/commands.py` → split en `commands/account.py` + `commands/availability.py`
  (mismo archivo, cero cambio de comportamiento, solo organización).
- `quotes/services/commands.py` — extraer el mismo patrón de helpers (`_reorder`/`_toggle_active`/
  `_soft_delete`/`_duplicate`) que ya usan `shop`/`renting`/`technical_services` para las 8 clases
  Command de taxonomía.

## 10. APIs simplificables

- Unificar los 2 endpoints de polling de Payment (`transaction-status/` vs `confirmation/`) en
  uno con un parámetro de "nivel de detalle", o documentar explícitamente por qué deben seguir
  separados (hoy la justificación vive solo en un comentario de código).
- Los 4 orquestadores admin duplicados (§9) implican que sus ViewSets base (`ProductCatalogChildViewSet`,
  `ServiceCatalogChildViewSet`, etc.) también podrían compartir una base común — mismo esfuerzo que
  fusionar los orquestadores, se recomienda hacerlos juntos.

## 11. Componentes reutilizables (lo que ya funciona bien — no tocar)

- `organization.SingletonMixin` — patrón correcto ya probado, candidato a reutilizar (§8/§9), no a
  reemplazar.
- `shared.ContentBlockConfig`/`CatalogRelation` — infraestructura genérica ya construida y
  verificada esta sesión (funciona para 2 content_types con órdenes por defecto independientes,
  sin romper ninguno).
- `CatalogListManager.vue` — ya generalizado con `parent-key`, usado por Renting/Shop/Technical
  Services sin fork.
- `ContentBlocksTab.vue` — ya generalizado con `entity-type`, usado por Shop/Technical Services.
- Familia `Equipment*.vue` (detalle público) — ya compartida por 3 módulos, solo pendiente de
  renombrar (deuda cosmética, no funcional).
- El patrón de helpers factorizados en `services/catalog.py` (Shop/Renting/Technical Services) —
  el que `quotes` debería adoptar (§9).

## 12. Documentación reducible

Cada uno de los 10 módulos auditados mostró alguna combinación de: contenido duplicado dentro del
mismo doc, changelog histórico mezclado con referencia de estado actual (Accounts: 37% del doc;
Payment: 6+ secciones "Bug corregido" intercaladas), o desactualización real frente al código
(Core: modelos/serializers eliminados que siguen en tablas de referencia; Renting: el modelo más
grande del módulo documentado con su forma vieja; Notifications: catálogo de plantillas
incompleto). **Recomendación estructural única aplicable a los 10 módulos:** separar cada
`ARQUITECTURA_COMPLETA_*.md` en 2 documentos — uno de **referencia de estado actual** (lo que el
brief pide: dominio, agregados, responsabilidades, eventos, flujos, APIs) y uno de **CHANGELOG**
append-only con las entradas fechadas — sin re-explicar el mismo campo/patrón más de una vez en el
documento de referencia.

## 13. Plan de refactorización por Sprint (Fase 9-10)

Cada sprint es independiente y no cambia lógica de negocio, contratos REST, eventos ni UX
(cumple los Principios Obligatorios del brief).

**Sprint 1 — Limpieza documental (todos los módulos, riesgo bajo, sin código):**
Separar referencia/changelog en los 10 docs; corregir las desactualizaciones puntuales listadas
en §5-6 de cada auditoría de módulo (conteos de modelos, tablas de serializers eliminados, doc de
`RentalRequest`, catálogo de plantillas de Notifications). Verificar si
`labor_conditions_evaluator.py` es código muerto.

**Sprint 2 — Modelos abstractos compartidos (riesgo bajo-medio):**
`shared.models.AbstractCostRule`/`AbstractCostAssignment` (clase base, sin migración de datos —
Shop/Renting/Services heredan). Adoptar `organization.SingletonMixin` en
`core.FooterCTAConfig/BrandSliderConfig/AboutUsConfig` y `payment.PaymentFeatureFlags`.

**Sprint 3 — Refactor Services (riesgo bajo, solo reorganización de archivos):**
Split `accounts/services/commands.py` en 2 archivos. Factorizar `quotes/services/commands.py` con
el patrón helper ya usado por Shop/Renting/Services. Split `payment/online/api/views.py` (ViewSet
/ sync / HMAC en archivos separados).

**Sprint 4 — Refactor API (riesgo medio):**
Unificar los 4 orquestadores admin de catálogo hijo en una clase genérica + su ViewSet base
compartido. Unificar `AdminProductContentBlockViewSet`/`AdminServiceContentBlockViewSet` (y su
par de Relation) en un ViewSet parametrizado por `module`.

**Sprint 5 — Refactor Frontend (riesgo bajo):**
Generalizar los 4 pares de managers Vue de catálogo (Specifications/Documents/Videos +
ProcessSteps) con el mismo patrón `entity-type` que ya probó `ContentBlocksTab.vue`. Renombrar (o
documentar explícitamente como intencional) la familia `Equipment*.vue`.

**Sprint 6 — Optimización final (riesgo medio-alto, requiere decisión de producto):**
Evaluar unificar el modelo Review (4→1, vía `ContentType`, mismo patrón que
`ContentBlockConfig`) — es el único cambio de este plan que toca datos existentes y contratos de
serializer, por eso queda al final y requiere aprobación explícita antes de ejecutar. Evaluar
separación de `technical_services` en sub-paquetes internos (catálogo/pricing/scheduling/FSM) sin
romper la app Django (reorganización de módulos Python, no de apps) — alto esfuerzo, beneficio
principalmente de mantenibilidad a largo plazo, no urgente.

## 14. Riesgos

| Riesgo | Mitigación |
|---|---|
| Unificar el modelo Review rompe 4 endpoints públicos existentes | Sprint 6 al final, con período de coexistencia (serializer nuevo aditivo antes de retirar los 4 viejos), mismo criterio ya aplicado 2 veces esta sesión con `ContentBlockConfig` |
| Fusionar orquestadores admin introduce una regresión sutil en algún módulo que dependía de un detalle de implementación no documentado | Cobertura de tests existente por módulo (Shop/Services ya tienen suites verificadas esta sesión) + tests nuevos antes de fusionar, no después |
| Reorganizar `technical_services` en sub-paquetes rompe imports en cascada (30 modelos, muchos callers) | Alto esfuerzo reconocido — Sprint 6, opcional, requiere aprobación explícita de negocio antes de iniciar |
| Limpieza documental (Sprint 1) parece "gratis" pero puede introducir NUEVA desactualización si no se automatiza | Considerar, a futuro, un check de CI que compare conteos de modelos/endpoints reales contra lo declarado en el doc (fuera de alcance de este plan, se deja como recomendación) |

## 15. Beneficios esperados

- Menos superficie de código para mantener sincronizada en cambios futuros (6 modelos de
  CostRule → 1 clase base; 4 orquestadores admin → 1; 4 pares de managers Vue → 1 generalizado).
- Documentación que refleja el estado real del sistema, reduciendo el riesgo (ya materializado 2
  veces esta sesión: `technical_services/CLAUDE.md` y el brief original de Renting) de que un
  agente o desarrollador tome una decisión basada en una afirmación desactualizada.
- Patrón `SingletonMixin`/`ContentBlockConfig`-style ya validado, reutilizable para el próximo
  módulo nuevo que necesite cualquiera de esos 2 patrones (evita repetir la duplicación otra vez
  en el módulo #11).

## 16. Arquitectura objetivo

Misma topología de módulos que hoy (el brief prohíbe explícitamente romper Bounded Contexts
existentes) con 3 piezas de infraestructura compartida nuevas o extendidas:
`shared.models.AbstractCostRule` (Sprint 2), un `GenericCatalogChildOrchestrator` factory en
`dashboard/services/` (Sprint 4), y — condicionado a aprobación de producto — un `Review`
genérico vía `ContentType` en `shared/` (Sprint 6), siguiendo exactamente el precedente ya sentado
por `ContentBlockConfig`/`CatalogRelation` esta sesión. `technical_services` mantiene su
responsabilidad ampliada (4 sub-dominios) documentada explícitamente como decisión consciente,
con la opción de sub-paquetes internos como mejora de mantenibilidad no bloqueante.

## 17. Checklist de validación (Fase 12 — compatibilidad)

Ninguna acción de este informe se ejecutó todavía (es un informe de auditoría, per el brief). Antes
de ejecutar CUALQUIER sprint del §13, validar para ese sprint específico:

- [ ] 0 cambios en reglas de negocio (Sprints 1-5 no tocan ningún Command de negocio; Sprint 6 sí — requiere aprobación aparte)
- [ ] 0 cambios en contratos REST/payloads/serializers públicos (Sprints 1-5: cierto por diseño — son refactors internos; Sprint 6 Review: requiere periodo de coexistencia aditivo)
- [ ] 0 cambios en eventos/flujos/Frontend/URLs/casos de uso/permisos/estados (todos los sprints)
- [ ] Suite de tests del módulo afectado pasa antes y después (mismo criterio ya aplicado 2 veces esta sesión: Shop 30/30, Technical Services 144/144)
- [ ] Cada cambio de Sprint 2+ mantiene compatibilidad hacia atrás explícita (migraciones aditivas, nunca destructivas, mismo patrón ya usado 2 veces esta sesión)

---

## Métricas de reducción (Fase 13) — estimación, no medición automatizada

| Métrica | Actual (aprox., de la documentación auditada) | Propuesto tras Sprints 1-5 | Reducción |
|---|---|---|---|
| Modelos "Regla de costo" | 6 (3 pares) | 6 tablas, 1 clase base compartida | ~66% código duplicado eliminado, 0% reducción de tablas |
| Orquestadores admin de catálogo hijo | 4 clases ~90 líneas c/u | 1 clase genérica | ~75% líneas de este patrón |
| Managers Vue de catálogo (Specs/Docs/Videos) | 7 archivos (~1500 líneas combinadas) | 3 archivos generalizados | ~55% líneas de este patrón |
| ViewSets admin ContentBlock/Relation | 4 clases | 2 clases (una por concern, parametrizada por módulo) | 50% |
| Documentación: líneas de changelog mezcladas en doc de referencia | ~35% del contenido total en los módulos más afectados (Accounts, Payment) | 0% (movido a CHANGELOG separado) | No es "eliminación", es reorganización — mejora la legibilidad sin perder historial |

No se calculan complejidad ciclomática/acoplamiento/cohesión de forma automatizada (fuera de
alcance de una auditoría manual basada en documentación — requeriría tooling estático que no se
ejecutó en esta pasada). Las cifras de arriba son conteos directos de los hallazgos con evidencia
de código, no estimaciones de una herramienta.
