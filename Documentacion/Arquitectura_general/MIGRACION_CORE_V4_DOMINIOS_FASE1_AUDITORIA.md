# CORE v4 — Arquitectura por Dominios: Fase 1 (Auditoría de Dominio)

**Fecha:** 2026-07-12
**Alcance:** Solo lectura. Ningún archivo de código fue modificado en esta fase.
**Mandato del usuario:** convertir el panel administrativo de una organización por componentes
técnicos (Home/Banners/Footer/Navbar/Marca/CTA) a un **Panel de Dominios** de 13 dominios
funcionales, con `organization` como único propietario de datos institucionales y comunicación
entre dominios exclusivamente vía Services/Selectors/APIs — nunca acceso directo a modelos de
otro dominio.

**Regla de proceso activa:** la IA actúa como Arquitecto Editor, una fase a la vez. Esta fase
(1) termina aquí y **espera autorización explícita** antes de proponer o tocar nada de la
Fase 2 (rediseño del panel) en adelante.

---

## 1. Inventario de apps actuales

19 apps de proyecto en `ecommerce_sintel/` (18 preexistentes + `organization`, creada esta
misma sesión):

`accounts`, `cart`, `core`, `dashboard`, `inventory`, `kyc`, `marketing`, `notifications`,
`operations`, `orders`, `organization`, `payment`, `quotes`, `renting`, `security`, `shop`,
`support`, `technical_services`, `users`.

`dashboard` tiene **0 modelos propios** (`dashboard/models.py` vacío) — es 100% BFF admin,
proxy sobre selectors/commands de otras apps. No posee dato alguno.

---

## 2. Mapa completo: Modelo → App actual → Dominio propuesto (v4)

| Dominio propuesto (v4) | App(s) actual(es) | Modelos | Estado |
|---|---|---|---|
| **1. Organization** | `organization` | `Company`, `Branding`, `ContactInfo`, `SocialLink`, `EmailSettings`, `DomainSettings`, `SeoSettings`, `LegalEntityInfo` | ✅ Ya migrado esta sesión (Fases 1-7 de la migración anterior) |
| **2. Sitio Web (Core)** | `core` | `HomeBanner`, `HomeModuleConfig`, `HomeCard`, `HomeCardGroup`, `FooterCTAConfig`, `FooterLink` (solo nav), `NavbarLink` | ✅ Ya alineado — `core` dejó de poseer datos institucionales en esta misma sesión, solo le queda contenido de página |
| **3. Catálogo** | `shop` | `Category`, `Brand`, `Product`, `ProductVariant`, `ProductImage`, `ProductReview`, `Tax`, `ProductCostRule`, `ProductCostAssignment` | ✅ Limpio — catálogo puro, sin mezcla operativa |
| **4. Servicios** | `technical_services` | `ServiceCategory`, `ServiceLevel`, `ServiceConfiguration`, `TechnicalService`, `ServiceVariant`, `ServiceMaterial`, `ServiceImage`, `ServiceReview`, `ServiceCostRule/Assignment`, `ServicePriceHistory` (catálogo) **+** `OrderServiceDetail`, `OrderServiceTimeline`, `ServiceAttachment`, `ServiceBooking`, **`ServiceOperation`**, `ServiceOperationEvent` (operativo) | ⚠️ **Mezclado**: catálogo + ciclo operativo post-pago (11 estados) en la misma app |
| **5. Renting** | `renting` | `RentingCategory`, `RentingBrand`, `Equipment`, `EquipmentVariant`, `EquipmentImage`, `EquipmentReview`, `RentalLabor`, `RentalCostRule/Assignment`, `EquipmentLogisticsConfig` (catálogo) **+** `RentalRequest`, `RentalProjectAttachment`, `RentalPeriod`, **`RentalOperation`**, `RentalOperationEvent` (operativo) | ⚠️ **Mezclado**: catálogo + wizard comercial + ciclo operativo post-pago (10 estados) en la misma app |
| **6. Marketing** | `marketing` | `MarketingCampaign`, `FlashOffer`, `PersonalOffer`, `CampaignLog`, `AgentRun`, `SalesAnalysis` | ✅ Limpio — patrón pull-based ya correcto (`SummaryProvider`, nunca importa modelos de otras apps) |
| **7. CRM** | **No existe ninguna app** | — | 🆕 Dominio nuevo. Único vestigio: `support.Customer360Selector` (100% lectura agregada, no almacena nada — ver sección 5) |
| **8. Ventas** | `quotes` + `orders` (parcial) + `payment` (parcial) | Cotizaciones: `Quotation` + 14 modelos satélite. Pedidos: `Order`, `OrderItem`, `Coupon`, `ShippingAddress`, `OrderItemCostSnapshot`. Pagos: `Transaction`, `CodTransaction`, `NequiTransaction`, `TokenizedCard` | ⚠️ Hoy son **3 apps con SSoT propio ya establecidas y documentadas** (`payment`=SSoT pagos, `orders`=SSoT pedidos, `quotes`=SSoT cotizaciones) — agruparlas bajo un dominio "Ventas" es viable como **agrupación de navegación**, fusionarlas físicamente es un cambio de mucho mayor riesgo |
| **9. Compras** | **No existe ninguna app** | — | 🆕 Dominio 100% nuevo — cero modelos de proveedores/órdenes de compra/recepciones en todo el proyecto |
| **10. Inventario** | `inventory` | `StockRecord` (GenericFK), `InventoryTransaction` | ✅ Limpio — ya es genérico/agnóstico por diseño |
| **11. Operaciones** | `operations` + `renting` (parcial) + `technical_services` (parcial) + `orders` (parcial) | `OperationTicket`, `OperationAssignment`, `TrackingEvent`, `OperationDocument`, `OperationReview`, `DispatcherProfile` (en `operations`) **+ duplicados**: `ServiceOperation`/`ServiceOperationEvent` (en `technical_services`), `RentalOperation`/`RentalOperationEvent` (en `renting`), `Shipment`/`ShipmentTimeline`/`ShipmentTrackingEvent` (en `orders`) | 🔴 **CRÍTICO — ver sección 3.1**: 3-4 máquinas de estado post-pago independientes para el mismo concepto |
| **12. RRHH** | **No existe ninguna app** | — | 🆕 Dominio 100% nuevo — cero modelos de empleados/nómina/contratos/vacaciones en todo el proyecto |
| **13. Configuración** | `users` + `accounts` (parcial) + `security` + `notifications` | Usuarios/auth: `User`, `PhoneOtp`, `EmailVerificationCode`, `UserAuditLog` (`users`). Perfiles/CV: `UserProfile`, `TechnicianProfile` + 9 modelos de CV (`accounts`). Auditoría/logs: `SecurityEvent` (`security`). Notificaciones: `NotificationTemplate`, `UserNotificationPreference`, `NotificationLog` (`notifications`) | ⚠️ Ver sección 4 — `accounts` mezcla auth-adyacente (perfil) con datos de "portafolio profesional" (CV/casos de éxito) que conceptualmente son más de **Operaciones/RRHH-proveedores** que de "Configuración" pura |
| *(sin dominio v4 explícito)* | `kyc` | `UserVerification`, `VerificationDocument`, `VerificationEvent`, `ConsentRecord` | ⚠️ No aparece en la lista de 13 dominios del usuario — encaja naturalmente en **Configuración** (verificación de identidad de usuarios) pero falta decisión explícita |
| *(sin dominio v4 explícito)* | `support` | `ChatRoom`, `ChatMessage`, `ChatRoomContext` | ⚠️ No aparece en la lista de 13 dominios — el usuario propone "CRM" que podría absorberlo, o podría quedar como su propio dominio "Soporte/Atención al Cliente" |

---

## 3. Redundancias detectadas

### 3.1 🔴 CRÍTICA — Triple (en la práctica, cuádruple) máquina de estados post-pago

**Hallazgo con evidencia de código, no solo de modelos.** Para el mismo evento de negocio (pago
confirmado), el sistema crea **simultáneamente y sin FK entre sí** varios registros de
"operación":

```python
# payment/shared/commands.py::confirm_order_payment (servicio tecnico)
ServiceCommands.confirm_slot_on_payment(order)     # -> technical_services.ServiceOperation (11 estados)
OperationCommands.ensure_tickets_for_order(order)  # -> operations.OperationTicket (9 estados, operation_type=SERVICE)

# renting/services/commands.py (renting)
ticket = OperationCommands.ensure_ticket_for_rental(rental_request)  # -> operations.OperationTicket
RentalOperationCommands.ensure_for_request(rental_request)           # -> renting.RentalOperation (10 estados)
```

Además, `orders.Shipment` (entrega de productos físicos) implementa **su propio** FSM de
picking/packing/despacho/entrega, con `ShipmentTimeline`/`ShipmentTrackingEvent` propios,
parcialmente enganchado a `operations.DispatcherProfile` vía `assigned_dispatcher` pero sin
pasar por `OperationTicket`.

**Resultado:** hasta 4 sistemas independientes (`operations.OperationTicket`,
`technical_services.ServiceOperation`, `renting.RentalOperation`, `orders.Shipment`) modelan el
mismo concepto ("ciclo operativo post-pago: recepción → planeación → asignación → ejecución →
cierre/incidente") con vocabularios de estado distintos pero solapados, cada uno con su propio
timeline y sin mecanismo de sincronización visible entre ellos. Es exactamente el riesgo que
`operations` fue diseñada para resolver (`operation_type` ya cubre SHOP_DELIVERY/RENTAL/SERVICE)
pero que en la práctica **nunca se terminó de centralizar**.

**Riesgo real:** un ticket puede quedar `COMPLETED` en `operations` mientras el
`ServiceOperation`/`RentalOperation` correspondiente sigue `IN_PROGRESS` (o viceversa), sin
ninguna alerta ni reconciliación automática.

### 3.2 Ya resuelta esta sesión — Company/Branding/Contacto/RedesSociales

`core.SiteBrandConfig`/`CompanyContactInfo`/`FooterLink(social)` → migrados a `organization`.
Ver `MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md`. No requiere acción en este plan.

### 3.3 Menor — "Integraciones" aparece en 2 dominios propuestos por el usuario

El plan v4 lista "Integraciones institucionales" bajo **Organization** y también
"Integraciones" (junto a Webhooks/API) bajo **Configuración**. Hoy solo existe un tipo de
integración externa real: credenciales de redes sociales para posteo automático
(`OrganizationSelector.get_integration_settings()`, fachada sobre `.env`). No hay webhooks
propios documentados fuera de `payment` (webhook de Wompi, ya gobernado por la SSoT de pagos).
**Requiere que el usuario aclare el límite** entre ambos antes de la Fase 2.

---

## 4. Responsabilidades mezcladas (más allá de 3.1)

- **`technical_services`** y **`renting`**: cada una mezcla 3 capas en una sola app — catálogo
  (categoría/marca/variante/precio), comercial (booking/wizard) y operativo post-pago (FSM).
  El propio código ya usa comentarios/docstrings que dicen explícitamente "dominio separado del
  comercial" para `ServiceOperation`/`RentalOperation` — la intención de separación ya existe,
  falta la separación física de app.
- **`accounts`**: mezcla datos de perfil de auth-adyacente (`UserProfile`, campos básicos) con
  un portafolio profesional completo (CV, certificaciones, casos de éxito, disponibilidad) que
  es conceptualmente más cercano a un dominio de "proveedores/contratistas" que a
  "Configuración". No hay un dominio v4 explícito para esto — el usuario deberá decidir si
  entra en RRHH (aunque RRHH en la propuesta es para EMPLEADOS internos, no contratistas
  externos, lo cual sería una mezcla distinta) o se queda en Configuración.
- **`dashboard`**: no es un dominio de negocio, es la capa de presentación/BFF del panel
  administrativo actual. Bajo el Panel de Dominios, su rol pasaría a ser transversal (cada
  dominio expondría su propia API admin) en vez de ser el único punto de agregación — esto es
  un cambio de fondo que toca Fase 2 (rediseño del panel) y Fase 5 (refactor por dominio), no
  esta fase.

---

## 5. Dominios nuevos sin app existente

| Dominio | Estado actual | Notas |
|---|---|---|
| **CRM** | No existe ninguna app ni modelo (`Prospect`/`Lead`/`Opportunity`/`Funnel`: cero resultados en todo el proyecto) | Único vestigio: `support.Customer360Selector` — confirmado 100% lectura agregada (docstring explícito: *"support nunca posee estos datos, ni los copia"*), agrega `accounts`+`kyc`+`orders`+`renting`+`notifications`+`support` en un timeline en memoria. Es un patrón sano que se podría **elevar** a un futuro dominio CRM sin tener que migrar datos (ya no duplica nada) |
| **Compras** | No existe ninguna app ni modelo (proveedores, órdenes de compra, recepciones, costos de compra: cero resultados) | Dominio 100% nuevo a construir desde cero, no una migración de datos existentes |
| **RRHH** | No existe ninguna app ni modelo (empleados, nómina, contratos, vacaciones: cero resultados) | Dominio 100% nuevo a construir desde cero |

---

## 6. Mapa de dependencias entre apps (grafo textual, dependencias reales confirmadas por FK/import)

```
organization (SSoT institucional)
    ← consumida por: core, notifications, accounts, users, marketing (Fase 6 ya completada)

users (auth)
    ← FK desde: accounts, orders, payment, quotes, renting, technical_services, shop,
                cart, kyc, support, security, notifications, operations (todas via AUTH_USER_MODEL)

accounts
    ← consumida por: kyc (reutiliza campos de identidad), operations (ProfessionalAvailability)

shop (catálogo productos)
    → depende de: inventory (StockRecord, InventoryCommands)
    ← consumida por: cart, orders (OrderItem), quotes (QuotationItem)

technical_services (catálogo + operación servicios)
    → depende de: shop (ServiceMaterial → ProductVariant), orders (OrderServiceDetail → Order),
                   accounts (ProfessionalAvailability)
    ← consumida por: cart (CartItem), orders (OrderItem), quotes (QuotationService)

renting (catálogo + operación renta)
    → depende de: operations (RentalOperation.assigned_dispatcher → DispatcherProfile)
    ← consumida por: orders (OrderItem), quotes (QuotationRentalItem), payment (Transaction/NequiTransaction)

orders
    → depende de: shop, technical_services, renting (OrderItem), operations (Shipment.assigned_dispatcher)
    ← consumida por: payment (Transaction/CodTransaction/NequiTransaction), technical_services
                      (OrderServiceDetail), operations (OperationTicket.source_order), support
                      (ChatRoomContext)

payment
    → depende de: orders, renting (Transaction/NequiTransaction referencian ambos)
    (no tiene consumidores hacia adentro — es hoja del grafo, correcto para una SSoT)

quotes
    → depende de: shop, technical_services, renting (solo snapshots de solo lectura, sin FK
      hacia orders/payment — confirmado, quotes es independiente del ciclo de venta real)

operations
    → depende de: orders, renting (OperationTicket.source_order/source_rental_request),
                   accounts (ProfessionalAvailability)
    ⚠️ NO está enlazada con technical_services.ServiceOperation ni renting.RentalOperation
       pese a modelar el mismo concepto (ver 3.1)

marketing
    → depende de: shop, renting, technical_services, orders (todo vía SummaryProvider pull-based,
      patrón correcto, sin FK directas)

support
    → depende de: orders, renting (ChatRoomContext), accounts+kyc+orders+renting+notifications
      (Customer360Selector, solo lectura)

notifications
    ← consumida por: prácticamente todas las apps (dispatch_notification como SSoT de notificaciones)

security
    ← consumida por: api_exceptions.py (throttling), kyc, payment, orders/cupones, inventory,
      operations, notifications (logging centralizado vía SecurityCommands.log_event)

dashboard
    → depende de: TODAS las apps (es el BFF admin, sin modelos propios)
```

---

## 7. Riesgos de migración (para las fases siguientes, no ejecutados en esta fase)

1. **Consolidar el triple FSM de operaciones (3.1) es el cambio de mayor riesgo técnico** de
   todo el plan — toca 4 apps, datos históricos reales en producción, y lógica de negocio activa
   (`payment/shared/commands.py::confirm_order_payment` dispara los 3 sistemas hoy). Requiere
   diseño cuidadoso de migración de datos + período de convivencia, no un simple `DeleteModel`.
2. **"Ventas" como fusión física de `quotes`+`orders`+`payment`** contradice las SSoT ya
   establecidas y documentadas explícitamente en `.AGENT.md` (secciones 7.3/7.4) — si la
   intención real es solo agrupación de **navegación** (menú), el riesgo es bajo (Fase 2); si es
   fusión de **apps físicas**, el riesgo es tan alto como el punto 1.
3. **CRM/Compras/RRHH son dominios sin ningún dato que migrar** — más simple que los anteriores
   (no hay redundancia que eliminar), pero implican diseño de dominio desde cero, con el mismo
   cuidado que se aplicó a `organization` (confirmar campos con el usuario antes de crear
   modelos, como se hizo en la Fase 4 de esa migración).
4. **`dashboard` sin modelos propios es una ventaja, no un riesgo** — al no poseer datos, su
   reorganización (Fase 2/6) es principalmente de navegación/UI, no de datos.

---

## 8. Plan de corrección (borrador para discusión — NO ejecutar sin autorización)

Basado en los hallazgos de arriba, un orden de fases sugerido (a confirmar/ajustar por el
usuario antes de la Fase 2):

1. Confirmar el límite entre "Integraciones" de Organization vs Configuración (3.3).
2. Decidir el destino de `kyc` y `support` en el mapa de 13 dominios (no estaban explícitos).
3. Decidir si "Ventas" es agrupación de navegación o fusión física de apps (riesgo 7.2).
4. Decidir el destino del portafolio profesional de `accounts` (RRHH-proveedores vs
   Configuración vs dominio propio).
5. Diseñar la consolidación del triple FSM de Operaciones (7.1) — el cambio más delicado,
   candidato a ser su propia mini-migración de varias fases dentro de la Fase 5.
6. Recién con 1-5 resueltos, proceder a Fase 2 (rediseño de navegación del panel).

---

## Estado

**Fase 1: COMPLETA.** Sin cambios de código. Este documento es el entregable (mapa de dominios,
redundancias, riesgos, plan de corrección borrador).

**⏳ Pendiente de autorización explícita para iniciar la Fase 2.**
