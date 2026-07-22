---
description: Mapa completo de rutas (customer + admin), reglas de navegacion y guards. Fuente de verdad para nombres de ruta validos.
metadata:
  domain: architecture
  supersedes: FRONTEND_SKILL.md (seccion 7), FRONTEND_COMPONENT_REGISTRY.md (raiz, seccion 6), FRONTEND_COMPONENT_REGISTRY.md (ecommerce_sintel, secciones 6-9)
  last_audited: "2026-07-11"
---

# Routing

## 1. Regla de navegacion

```js
// Siempre por name, nunca hardcodear paths
router.push({ name: 'product-detail', params: { uuid: product.uuid } });
router.push({ name: 'shop-catalog', query: { q: searchTerm } });
```

## 2. Navigation guards — `src/apps/admin/router.js`

- `meta.requiresAuth` → redirige a `/login` si no autenticado.
- `meta.requiresAdmin` → redirige a `/` si no es admin (`is_staff !== true`).
- `meta.requiresGuest` → usado en rutas de auth y en `mi-cuenta/verificacion` (ver
  [[project_ssot_identity_customer_first]] en memoria — no usar `useRouter()` dentro de
  `router.beforeEach`, no es seguro ahi).
- **Rutas cliente deben usar siempre `CustomerLayout`** — nunca declararlas top-level en
  `router.js` o se pierde navbar/footer. Ver [[feedback_customer_routes_layout]].

## 3. Rutas publicas / auth

| name | path | auth |
|------|------|------|
| `home` | `/` (LandingView, publica) | no |
| — | `/inicio` (HomeView, autenticado) | si |
| — | `/login` (LoginView) | guest |
| — | `/registro` (RegisterView) | guest |
| — | `/registro/contratista` (RegisterContractorView) | guest |
| — | `/verificar-cuenta` (VerifyEmailLinkView, publica) | no |

`RegisterContractorView` incluye el tipo de perfil `CONTRACTOR` ademas de
TECHNICIAN/PROFESSIONAL/SPECIALIST.

## 4. Rutas customer — Tienda / Alquiler / Servicios

| name | path | auth |
|------|------|------|
| `about-us` | `/nosotros` | no |
| `shop-catalog` | `/tienda` | no |
| `product-detail` | `/tienda/producto/:uuid` | no |
| `rental-catalog` | `/alquiler` | no |
| `rental-detail` | `/alquiler/equipo/:uuid` | no |
| `rental-request` | `/alquiler/equipo/:uuid/solicitar` | si |
| `services-catalog` | `/servicios` | no |
| `service-detail` | `/servicios/:uuid` | no |
| `service-request` | `/servicios/:uuid/solicitar` | si |
| `contractor-selection` | `/servicios/:uuid/profesional` | si |
| `schedule-selection` | `/servicios/:uuid/horario/:profileUuid` | si |
| `quote-wizard` | `/cotizar` | no |

`ServicesCatalogView` tiene CTA "Quiero ofrecer mis servicios" que enlaza a `/registro-profesional`.

## 5. Rutas customer — Checkout / Mi cuenta / Contratistas

| name | path | auth |
|------|------|------|
| `checkout` | `/checkout` | si |
| `order-confirmed` | `/orden-confirmada` | no |
| — | `/checkout/nequi-pendiente` (NequiPendingView) | si |
| `customer-profile` | `/mi-cuenta/perfil` | si |
| `customer-orders` | `/mi-cuenta/pedidos` | si |
| `customer-wishlist` | `/mi-cuenta/wishlist` | si |
| `customer-addresses` | `/mi-cuenta/direcciones` | si |
| `customer-cards` | `/mi-cuenta/tarjetas` | si |
| `customer-quotes` | `/mi-cuenta/cotizaciones` | si |
| — | `/mi-cuenta/onboarding` (ContractorOnboardingWizard) | si |
| — | `/mi-cuenta/agenda` (ContractorScheduleView) | si |
| — | `/mi-cuenta/verificacion` (existe por el guard `requiresGuest` — ver [[project_ssot_identity_customer_first]]) | si |
| `contractor-marketplace` | `/contratistas` | no |
| `contractor-profile` | `/contratistas/:uuid` | no |
| — | `/operaciones` (OperationListView) | si |
| — | `/operaciones/:uuid` (OperationTrackingView) | si |

## 6. Rutas panel admin

| name | path | app backend |
|---|---|---|
| `dashboard` | `/panel/dashboard` | dashboard/ |
| `product-list` | `/panel/productos` | shop/ |
| `category-list` | `/panel/categorias` | shop/ |
| `brand-list` | `/panel/marcas` | shop/ |
| — | `/panel/impuestos` (TaxList) | shop/ |
| `inventory` | `/panel/inventario` | inventory/ |
| `orders` | `/panel/ordenes` | orders/ |
| `quotes` | `/panel/cotizaciones` | quotes/ |
| `services` | `/panel/servicios` | technical_services/ |
| — | `/panel/s-categorias` (ServiceCategoryList) | technical_services/ |
| — | `/panel/s-niveles` (ServiceLevelList) | technical_services/ |
| `renting` | `/panel/renta` | renting/ |
| `equipment-detail` | `/panel/renta/:uuid` (tabs: Variantes/Logistica/Reglas de Costo/Bloqueos, 2026-07-14) | renting/ |
| — | `/panel/r-categorias` (RentingCategoryList) | renting/ |
| — | `/panel/r-marcas` (RentingBrandList) | renting/ |
| — | `/panel/r-labor` (RentalLaborList) | renting/ |
| `renting-requests` | `/panel/renta/solicitudes` (2026-07-07, grupo "Renta") | renting/ |
| `marketing` | `/panel/marketing` | marketing/ |
| `support` | `/panel/soporte` | support/ |
| `home-config` | `/panel/home-config` | core/ |
| `about-us-admin` | `/panel/nosotros` (2026-07-19, grupo "Sitio Web") | core/ |
| — | `/panel/usuarios` (UserList) | users/ |
| `professionals-admin-list` | `/panel/profesionales` (grupo "Serv. Tecnicos") | accounts/ |
| `technician-assignment-board` | `/panel/asignacion-tecnicos` (grupo "Logistica") | technical_services/ + orders/ |
| `security` | `/panel/seguridad` (SecurityDashboardView) | dashboard/ (proxy de security/) |
| `notifications-admin` | `/panel/notificaciones` (NotificationsAdminView, 2026-07-11) | dashboard/ (proxy de notifications/) |
| `payment-transactions` | `/panel/pagos` (PaymentTransactionsAdminView, 2026-07-11) | dashboard/ (proxy de payment/) |
| — | `/admin/login` (AdminLoginPage) | auth/ |
| — | `/panel/perfil` (ProfileView) | accounts/ |

**Nota (auditoria enterprise_sync 2026-07-11):** la ruta huerfana `/inicio` (`LandingView.vue`,
top-level fuera de `CustomerLayout`, contenido hardcodeado) fue eliminada — ver
[../editor/enterprise_sync_audit_2026_07_11.md](../editor/enterprise_sync_audit_2026_07_11.md).
La home real sigue siendo `HomeView.vue` en `/`.

**[CRITICAL] Dos sistemas de asignacion paralelos, deliberadamente separados:** `OperationBoard`/
`OperationDetail` (generico `operations.OperationTicket`, cubre SHOP_DELIVERY/RENTAL/SERVICE) y
`TechnicianAssignmentBoard` (especializado `technical_services.ServiceAssignmentCommands`, solo
servicios tecnicos) — ambos viven en el grupo "Logistica" del sidebar pero NO son la misma
pantalla ni el mismo modelo de datos. No fusionar sin instruccion explicita. Detalle completo:
`technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` §17.1.

`RentingRequestList` no tiene ruta de detalle separada: cada fila expande
`RentalRequestActionsPanel` inline (mismo mecanismo que `pendingDelete`, ver
[../components/dialogs.md](../components/dialogs.md)).

## Ver tambien

- [../components/cards.md](../components/cards.md) — inventario completo de vistas y componentes por ruta
- [state_management.md](state_management.md) — stores que alimentan cada modulo
