# CORE v4 — Arquitectura por Dominios: Fase 3 (Validación de Propiedad de Datos)

**Fecha:** 2026-07-12
**Alcance:** Solo lectura/validación. Cero cambios de código en esta fase.
**Método:** grep sistemático de `from <app>.models import` en todo `ecommerce_sintel/**/*.py`
(231 resultados), filtrado de tests (esperado que importen modelos directo para fixtures) y de
imports del mismo dominio (esperado), clasificación del resto por patrón de acceso real.

---

## 1. Matriz "Dato → Propietario → Consumidores"

Formalización del grafo de dependencias de la Fase 1, ahora con el **mecanismo de acceso real**
verificado en código (Selector/Service vs. import de modelo directo) y marca de cumplimiento.

| Dato | Propietario (dominio) | Consumidores | Mecanismo real | Cumple regla "solo vía Service" |
|---|---|---|---|---|
| Stock (`StockRecord`) | Inventario | shop, cart, payment (deducción post-pago) | `InventorySelector`/`InventoryCommands` (con excepción documentada: lectura en ruta de escritura usa el campo bloqueado, no el selector — regla `.AGENT.md` 14.1) | ✅ |
| Productos/Variantes (`Product`, `ProductVariant`) | Catálogo (shop) | cart, orders, quotes, marketing (summary), technical_services (materiales) | `ProductSelector` en la mayoría; **FK estructural** en `OrderItem`/`CartItem`/`FlashOffer`/`ServiceMaterial` (ver 2.A) | ✅ (FK) / ⚠️ ver 3.3 (quotes) |
| Servicios/Variantes (`TechnicalService`, `ServiceVariant`) | Servicios | cart, orders, quotes, marketing | `ServiceSelector` en la mayoría; FK estructural en `OrderItem`/`CartItem` | ✅ (FK) / ⚠️ ver 3.3 (quotes) |
| Equipos/Variantes (`Equipment`, `EquipmentVariant`) | Renting | orders, quotes, marketing | FK estructural en `OrderItem` | ✅ (FK) |
| Pedido (`Order`, `OrderItem`) | Ventas › Orders | payment, technical_services (OrderServiceDetail), operations, support (ChatRoomContext), shop/renting/technical_services (`summary.py`) | Mezcla: `OrderSelector` en algunos, **`Order.objects.select_for_update()` directo en `payment`** (ver 3.1), `OrderItem` importado directo en 3 `summary.py` (ver 3.2) | ⚠️ ver 3.1, 3.2 |
| Pago (`Transaction`, `CodTransaction`, `NequiTransaction`, `TokenizedCard`) | Ventas › Payment | orders (indirecto vía `confirm_order_payment`), core (`enums()`) | `payment` es hoja del grafo — nadie más escribe estos modelos. `core.api.views.enums()` lee `Transaction.STATUS_CHOICES` (ver 3.4) | ✅ |
| Cotización (`Quotation` + 14 satélite) | Ventas › Quotes | *(nadie — quotes es consumidor puro, no productor para otros dominios)* | N/A | ✅ |
| Carrito (`Cart`, `CartItem`) | Cart | orders (checkout) | **`orders/services/commands.py` importa `cart.models.Cart` directo** (ver 3.5) | ⚠️ ver 3.5 |
| Operación genérica (`OperationTicket`) | Operaciones | core (`enums()`) | Selector propio (`operations.services.selectors`); core solo lee `STATUS_CHOICES` | ✅ / ⚠️ ver 3.4 |
| Operación de servicio (`ServiceOperation`) | **Servicios (debería ser Operaciones — ver Fase 1, 3.1)** | core (`enums()`) | Selector propio dentro de `technical_services` | ✅ (dentro de su app) / 🔴 ver Fase 1 hallazgo crítico |
| Operación de renta (`RentalOperation`) | **Renting (debería ser Operaciones — ver Fase 1, 3.1)** | — | Selector propio dentro de `renting` | ✅ (dentro de su app) / 🔴 ver Fase 1 hallazgo crítico |
| Envío (`Shipment`) | Ventas › Orders (subdominio logística) | operations (`assigned_dispatcher` FK) | Selectors propios (`orders.services.fulfillment.*`) | ✅ |
| Despachador (`DispatcherProfile`) | Operaciones | orders (`Shipment.assigned_dispatcher`), renting (`RentalOperation.assigned_dispatcher`) | FK estructural + import directo en `renting/api/operation_serializers.py` para serialización anidada | ✅ |
| Perfil de usuario (`UserProfile`) | Proveedores/Contratistas (`accounts`) | kyc (reutiliza campos, no duplica), core (`enums()`), users (admin) | `ProfileResolver` es el único punto de acceso mandado por `.AGENT.md` — cumplido en el código revisado | ✅ |
| Portafolio profesional (CV, certificaciones, disponibilidad) | Proveedores/Contratistas (`accounts`) | technical_services/renting (`ProfessionalAvailability` vía `OperationAssignment`) | FK directa a `ProfessionalAvailability` | ✅ |
| Verificación KYC (`UserVerification` + satélite) | Configuración (`kyc`) | accounts (`_assert_kyc_approved`), core (`enums()`) | `KycSelector` | ✅ |
| Auth (`User`) | Configuración (`users`) | **todas las apps** (`AUTH_USER_MODEL`, FK estándar de Django) | FK estándar — no es una "violación", es el mecanismo nativo de Django para autenticación | ✅ |
| Auditoría de seguridad (`SecurityEvent`) | Configuración (`security`) | kyc, payment, orders/cupones, inventory, operations, notifications (todos vía `SecurityCommands.log_event()`) | Command centralizado, nunca acceso directo desde otras apps | ✅ |
| Notificaciones (`NotificationTemplate`, `NotificationLog`) | Configuración (`notifications`) | prácticamente todas las apps | `NotificationCommands.dispatch_notification` SSoT — regla `.AGENT.md` 7.3, cumplida | ✅ |
| Chat (`ChatRoom`, `ChatMessage`, `ChatRoomContext`) | Soporte | *(nadie — support es consumidor puro de otras apps vía `Customer360Selector`)* | N/A, y `Customer360Selector` en sí mismo es 100% lectura agregada (confirmado Fase 1) | ✅ |
| Campaña/Oferta (`MarketingCampaign`, `FlashOffer`, `PersonalOffer`) | Marketing | *(nadie)* | N/A | ✅ |
| Datos institucionales (`Company`, `Branding`, `ContactInfo`, `SocialLink`, `EmailSettings`, etc.) | **Organization** | core, notifications, accounts, users, marketing | `OrganizationSelector`/`OrganizationCommands` — migración ya completada y verificada esta sesión | ✅ |
| Contenido de página (`HomeBanner`, `HomeCard`, `FooterCTAConfig`, `NavbarLink`, `FooterLink` nav) | Sitio Web (`core`) | dashboard (proxy admin) | `core.services.selectors` | ✅ |

---

## 2. Patrones de acceso cross-domain (clasificación)

### 2.A FK estructural entre dominios — ACEPTADO, no es una violación
`OrderItem.variant/service_variant/equipment_variant`, `CartItem.variant/service_variant`,
`FlashOffer.variant/service_variant/equipment_variant`, `ServiceMaterial.product_variant`,
`WishlistItem.variant` — son relaciones de base de datos normales (un pedido *necesita* apuntar
a qué producto compró). El import del modelo en `models.py` para declarar el `ForeignKey` es
inevitable y no viola "propiedad de datos": el dominio dueño (`orders`, `cart`, `marketing`,
`technical_services`) sigue sin **escribir** en los modelos de `shop`/`technical_services`/
`renting`, solo los referencia por FK. **No requiere ninguna migración.**

### 2.B Patrón `summary.py` (pull-based) — mayormente correcto, con una laguna real
La regla documentada (`.AGENT.md` 7.2) es que **`marketing` nunca debe importar modelos de
shop/renting/technical_services directamente** — debe usar `SummaryProvider.get_summary()`.
Confirmado en código: `marketing/services/selectors.py` no importa `shop.models` ni
`technical_services.models` ni `renting.models`. **Esta regla se cumple.**

Lo que la regla **no cubre** (laguna real, no una violación de una regla existente, sino un
vacío de diseño): `shop/services/summary.py`, `technical_services/services/summary.py` y
`renting/services/summary.py` **sí importan `orders.models.OrderItem` directamente** para
calcular estadísticas de ventas (top-selling, ingresos). No hay un `OrderSelector` específico
para "ítems vendidos de mi catálogo" — cada dominio resuelve el problema importando el modelo
de `orders` directo.

### 2.C `core.api.views.py::enums()` — acoplamiento de solo lectura, ya documentado
Importa `STATUS_CHOICES`/modelos de 8 dominios distintos (operations, orders, technical_services,
payment, quotes, renting, accounts, kyc) para construir catálogos de badges/labels del frontend.
Es lectura de metadata de clase (`Model.STATUS_CHOICES`), no de datos ni instancias — y ya está
documentado como decisión consciente en `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md`
("no hay indirección vía signal ni registro dinámico"). **No se recomienda tocar en esta
migración** — es un costo de acoplamiento bajo y ya visible/documentado, no oculto.

### 2.D `dashboard` — BFF sin modelos propios, importa modelo directo en vez de Selector en varios puntos
`dashboard/services/admin_orchestrators.py` importa modelos de `users`, `technical_services`,
`renting`, `orders`, `shop`, `marketing` directamente (no siempre vía sus Selectors). Como
`dashboard` no posee ningún dato propio (confirmado Fase 2), esto no es una violación de
"propiedad de datos" en sentido estricto — nadie más puede reclamar ese dato porque dashboard no
lo guarda — pero sí es una inconsistencia de patrón frente al resto del proyecto, que preferiría
que incluso los BFF pasen por los Selectors de cada dominio (más fácil de mantener si el modelo
de origen cambia). Candidato a limpieza en Fase 5, prioridad baja.

---

## 3. Migraciones pendientes concretas (para decidir en Fase 4, no ejecutadas aquí)

| # | Hallazgo | Severidad | Acción propuesta |
|---|---|---|---|
| 3.1 | `payment/shared/commands.py::confirm_order_payment` usa `Order.objects.select_for_update().get(pk=...)` directo, no vía `OrderSelector` | Baja — necesidad técnica real (row-lock transaccional que ningún Selector actual expone) | No migrar sin necesidad — documentar como excepción legítima en `.AGENT.md`, no forzar un `OrderSelector.get_for_update()` artificial |
| 3.2 | `shop`/`technical_services`/`renting` `services/summary.py` importan `orders.models.OrderItem` directo | Media — laguna de diseño, no viola ninguna regla escrita pero sí el espíritu del patrón pull-based | Crear `OrderSelector.get_items_for_variant_type(...)` o similar y migrar los 3 `summary.py` a usarlo |
| 3.3 | `quotes/services/commands.py` importa `shop.models.ProductVariant` y `technical_services.models.ServiceVariant` directo para construir snapshots | Baja — uso de solo lectura (`.objects.get(uuid=...)`), no escribe nada ajeno | Migrar a `ProductSelector.get_by_uuid()` / `ServiceSelector.get_by_uuid()` cuando se toque `quotes` por otra razón — no urgente por sí solo |
| 3.4 | `core/api/views.py::enums()` importa modelos de 8 dominios para leer `STATUS_CHOICES` | Baja — ya documentado, acoplamiento de metadata no de datos | Sin acción — aceptar como excepción documentada |
| 3.5 | `orders/services/commands.py` importa `cart.models.Cart` directo para checkout | Baja — necesita iterar ítems completos del carrito, un caso de uso específico de checkout | Migrar a `CartSelector.get_cart_with_items(user)` si `cart` alguna vez cambia su modelo interno; no urgente |
| 3.6 | `dashboard/services/admin_orchestrators.py` importa modelos de 6 dominios directo | Baja — dashboard no posee datos, es agregador BFF por diseño | Limpieza de consistencia en Fase 5, no bloqueante |
| 3.7 | **Triple/cuádruple FSM de Operaciones** (heredado de Fase 1, sección 3.1) | 🔴 **Alta — ya identificado como el hallazgo crítico del plan completo** | Ver plan de corrección de Fase 1; requiere diseño dedicado en Fase 5, no es un simple cambio de import |

**Nada de lo encontrado en esta fase es una violación grave nueva.** El proyecto ya sigue
disciplinadamente el patrón Service Layer / pull-based en la gran mayoría de los casos
(`marketing` cumple al 100% su regla de no importar modelos directos; `notifications` y
`security` son consumidos exclusivamente vía Commands centralizados; `organization` y `core`
quedaron perfectamente limpios tras la migración de esta misma sesión). Los 6 hallazgos
concretos (3.1-3.6) son de severidad baja/media — ninguno bloquea avanzar a la Fase 4. El único
punto de severidad alta (3.7) ya estaba identificado desde la Fase 1 y no cambia de tamaño con
esta validación adicional.

---

## Estado

**Fase 3: COMPLETA.** Cero cambios de código. Entregable: matriz de propiedad de datos (sección
1), clasificación de patrones (sección 2), lista de 7 migraciones pendientes (sección 3).

**⏳ Pendiente de autorización explícita para iniciar la Fase 4** (Eliminación de Redundancias
— con este alcance, sería principalmente decidir cuáles de 3.1-3.6 ejecutar ahora vs. diferir,
más el diseño de la consolidación del hallazgo 3.7/crítico de Fase 1, que probablemente merece
su propia sub-secuencia de fases dado su tamaño y riesgo).
