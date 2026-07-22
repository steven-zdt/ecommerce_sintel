---
description: Resultado real de la auditoria enterprise_sync.md ejecutada el 2026-07-11 — 17 modulos x 12 puntos. Las 3 fases de correccion fueron autorizadas y aplicadas el mismo dia.
metadata:
  domain: editor
  status: auditoria-y-correcciones-completadas
  last_audited: "2026-07-11"
---

# Auditoria Enterprise Sync — Resultado (2026-07-11)

Ejecutada segun el framework de [enterprise_sync.md](enterprise_sync.md). Metodo: datos
estructurales de `ai_engine/AI_MANIFESTS/*.json` (recien regenerados, ver
[[project_ai_engine_sync_2026_07_11]]) + verificacion manual de rutas/consumo frontend contra
[../architecture/routing.md](../architecture/routing.md) y
[../components/cards.md](../components/cards.md) + busqueda dirigida de hardcode en el portal
publico (agente de exploracion + verificacion manual propia).

**Nota de metodo:** el cruce automatico `frontend_consumers` de los manifiestos tiene falsos
negativos conocidos (ej. marca "security: 0 consumidores frontend" porque el endpoint real que
usa el frontend vive en el manifest de `dashboard`, no en el de `security` — se verifico caso por
caso antes de reportarlo como gap real).

---

## Fase 0 — Backend: Command / Selector / Serializer / ViewSet / Endpoint (puntos 3-6 del checklist)

Los 17 modulos tienen los 4 elementos presentes (verificado en `AI_MANIFESTS/*.json`, generado
2026-07-11):

| Modulo | Commands | Selectors | Serializers | ViewSets | Endpoints |
|---|---|---|---|---|---|
| core | 0* | 15 | 23 | 1 | via dashboard |
| marketing | 1 | 1 | 5 | 4 | 4 |
| shop | 7 | 5 | 15 | 5 | 5 |
| renting | 8 | 3 | 30 | 8 | 7 |
| technical_services | 11 | 7 | 40 | 7 | 6 |
| quotes | 10 | 9 | 35 | 4 | 4 |
| inventory | 1 | 2 | 5 | 2 | 2 |
| users | 3 | 2 | 8 | 1 | 0** |
| accounts | 2 | 5 | 24 | 11 | 10 |
| kyc | 1 | 1 | 14 | 3 | 2 |
| operations | 2 | 2 | 14 | 4 | 2 |
| dashboard | 0*** | 0*** | 0 | 36 | 37 |
| support | 1 | 1 | 4 | 0**** | 0**** |
| notifications | 1 | 0 | 3 | 2 | 2 |
| payment | 4 | 1 | 4 | 3 | 0** |
| orders | 2 | 3 | 19 | 2 | 3 |
| security | 1 | 1 | 1 | 1 | 1 |

`*` core: `HomeConfigCommands` esta clasificado como selector por el AST (heuristica de nombre),
no es un gap real. `**` users/payment: el AST no detecto router.register en su urls.py (usan
`path()` directo o vistas basadas en `APIView`, no `ViewSet` con router) — no es necesariamente un
gap, es una diferencia de patron; no verificado si users/payment deberian exponer mas endpoints
via router. `***` dashboard es un BFF sin logica propia por diseno (constraint documentada). `****`
support es websocket puro (`SupportChatConsumer`), no expone ViewSets REST — por diseno, ver
[[project_implementation_summary_audit]].

**Conclusion Fase 0:** no hay modulos sin capa de servicio backend. Los `**`/`***`/`****` son
patrones de diseno conocidos, no gaps.

---

## Fase 1 — Frontend: CRUD admin / ruta / consumo API (puntos 1, 2, 7, 8)

Verificado contra [../architecture/routing.md](../architecture/routing.md) y
[../components/cards.md](../components/cards.md) (construidos por lectura directa de codigo, no
solo el cruce automatico):

| Modulo | CRUD admin (`/panel/*`) | Endpoint dashboard | Consumo API real |
|---|---|---|---|
| core | HomeConfigView (`/panel/home-config`) | `dashboard/site-brand,banners,modules,home-cards/` | OK |
| marketing | MarketingView, CampaignForm | `marketing/dashboard/` | OK |
| shop | ProductList/Form, CategoryList, BrandList, TaxList | `dashboard/products,categories,brands,taxes/` | OK |
| renting | RentingList/Form/Detail, RentingRequestList | `dashboard/equipment,...` + `renting/rental-requests/` directo | OK |
| technical_services | ServiceList/Form/Detail, TechnicianAssignmentBoard | `dashboard/services,...` | OK |
| quotes | QuotationList/Detail | `quotes/quotations/` | OK |
| inventory | InventoryList | `inventory/stock-records/` | OK |
| users | UserList/Form/Detail | `users/` | OK |
| accounts | ProfessionalsAdminList | `auth/admin/professionals/` | OK |
| kyc | KycAdminList/Detail, KycVerificationPanel (en UserDetail) | `dashboard/` (via users) + `api/v1/auth/` | OK |
| operations | OperationBoard/Detail, DispatcherList | `operations/` | OK |
| dashboard | (es el BFF, no tiene UI propia) | n/a | n/a |
| support | SupportDashboardView | `support/` (+ websocket) | OK |
| notifications | (sin panel admin dedicado detectado) | `notifications/` | **Ver hallazgo H1** |
| payment | (sin panel admin dedicado — se ve dentro de Orders) | `payment/` | Parcial, ver H2 |
| orders | OrderList/Detail | `orders/orders/` | OK |
| security | SecurityDashboardView (`/panel/seguridad`) | `dashboard/security-events/` | OK |

### Hallazgo H1 — `notifications`: sin panel admin dedicado

No se encontro una vista admin tipo `NotificationList`/`NotificationLog` en `/panel/*`. Existe
`CustomerNotificationsView` (portal cliente) pero no un panel de administracion de plantillas
(`NotificationTemplate`) ni de logs (`NotificationLog`) para el equipo Sintel. Severidad: **media**
— hay 8 `NotificationTemplate` seed en BD (ver [[project_notifications_communication_center]]) que
hoy solo se pueden inspeccionar/editar por shell o admin de Django, no desde el Panel — esto
contradice parcialmente la regla "todo se administra desde el Panel".

### Hallazgo H2 — `payment`: sin vista propia, solo visible via Orders

No hay un `PaymentList`/`TransactionList` dedicado; las transacciones de pago solo se ven
indirectamente dentro del detalle de una orden. Severidad: **baja** — es un patron razonable (el
pago es 1:1 con la orden en la mayoria de los flujos), no necesariamente un gap, pero no hay forma
de auditar transacciones Wompi/Nequi/COD fallidas de forma centralizada desde el Panel.

---

## Fase 2 — Hardcode / duplicados / config local en el Portal Publico (puntos 9-12)

### Hallazgo H3 — CRITICO: `/inicio` (`LandingView.vue`) es una pagina huerfana con contenido 100% hardcodeado y ADEMAS rompe la regla de `CustomerLayout`

- `src/apps/admin/router.js:88-92` registra `/inicio` -> `LandingView` **top-level**, fuera de los
  `children` de `CustomerLayout` — exactamente el antipatron que ya esta documentado como
  prohibido en `frontend/CLAUDE.md` ("Rutas publicas orientadas al cliente — CRITICA") y en
  memoria [[feedback_customer_routes_layout]] (bug real historico: `/register` y
  `/registro-profesional` sufrieron esto mismo hasta 2026-07-06).
- `LandingView.vue` no hace ninguna llamada `useApi()`/store — tiene arrays hardcodeados
  (`heroFeatures` L117-122, `businessModules` L124-140) y copyright fijo (L92).
- La home REAL y correcta es `HomeView.vue` en `/` (dentro de `CustomerLayout`), que SI carga
  `core/home-feed/` + `core/site-config/` correctamente (`Promise.all` en L197-199) — `LandingView`
  parece un remanente pre-migracion que nunca se elimino.
- Sin navbar/footer de cliente (por estar fuera de `CustomerLayout`) + contenido desactualizado
  respecto al home real = dos violaciones simultaneas de reglas ya establecidas en el proyecto.

**Severidad: alta.** Es el unico hallazgo que viola la letra literal de la regla central del
framework ("nunca debe existir... contenido definido unicamente en el frontend publico").

### Hallazgos menores (severidad baja, NO se recomienda accion salvo que el usuario lo pida)

Estos son textos de interfaz (chrome de UI: botones de login, labels de navegacion interna,
copyright), no "contenido de negocio" en el sentido que apunta la regla (catalogos, precios,
textos de marketing). Convertirlos en configuracion editable seria sobre-ingenieria para el
beneficio real:

- `CustomerNavbar.vue` L96-114/126-130 — labels "Mi perfil", "Entrar", "Registrarse", etc.
- `CustomerFooter.vue` L119 — linea de copyright fija.
- `HomeView.vue` L50-76 — eyebrow/title/link-label de las 3 `FeaturedSection` (ya el contenido de
  los items SI viene de la API; solo el titulo de cada bloque esta fijo).
- `AccountSidebar.vue` L54-63 — navegacion interna del panel de cliente, ligada a rutas fijas.
- `TrustSection.vue`/`TrustCard.vue` — codigo muerto, no importados en ningun lado. No es
  violacion de la regla, es limpieza de codigo (deuda tecnica, no urgente).

No se encontraron duplicados de logica de negocio ni configuraciones en `localStorage` fuera de lo
ya documentado (`sintel_access`/`sintel_refresh` para tokens, `bookingStore` para el borrador del
wizard de renta — ambos son estado de sesion legitimo, no config de negocio).

---

## Resumen ejecutivo

| Severidad | Hallazgo | Modulo |
|---|---|---|
| Alta | `/inicio` (LandingView) huerfano, hardcodeado, fuera de CustomerLayout | core / routing |
| Media | Sin panel admin para NotificationTemplate/NotificationLog | notifications |
| Baja | Sin vista centralizada de transacciones de pago | payment |
| Baja (sin accion recomendada) | Textos de UI chrome hardcodeados (labels, copyright) | navbar/footer/home/account |
| Deuda tecnica (sin accion recomendada) | TrustSection/TrustCard no importados | landing |

17/17 modulos tienen capa de servicio backend completa (Command+Selector+Serializer+ViewSet+Endpoint).
15/17 tienen CRUD admin + ruta frontend + consumo API completo. 2 hallazgos de severidad
media/alta requieren decision del usuario antes de corregir.

---

## Fases de correccion — APLICADAS 2026-07-11

El usuario autorizo ejecutar las 3 fases en orden. Resultado:

### Fase de correccion 1 — Eliminar `/inicio` (LandingView.vue) — severidad ALTA — HECHO

Se verifico primero que no hubiera ninguna referencia a `{ name: 'landing' }` ni `/inicio` en todo
`frontend/src` (solo su propia declaracion de ruta). El sistema pidio confirmacion explicita de
Opcion A vs B antes del borrado fisico del archivo (bloqueo automatico de la accion destructiva);
el usuario confirmo Opcion A. Se elimino:
- El import y la entrada de ruta `/inicio` en `frontend/src/apps/admin/router.js`.
- El archivo `frontend/src/views/LandingView.vue`.

### Fase de correccion 2 — Panel admin para Notifications — severidad MEDIA — HECHO

Backend (nuevo, siguiendo el patron Command/Selector/Orchestrator/ViewSet del proyecto):
- `notifications/api/serializers.py`: `NotificationTemplateSerializer` extendido con
  `subject`/`email_body`/`whatsapp_template_name`/`created_at` (era un serializer sin uso real en
  ningun lado, se extendio sin riesgo de romper consumidores existentes).
- `notifications/services/selectors.py` (nuevo): `NotificationSelector` (`list_templates`,
  `get_template_by_uuid`, `list_logs` con filtros status/channel/template_slug/user_uuid).
- `notifications/services/commands.py`: `NotificationTemplateCommands.update_template` (allowlist
  de campos editables, el `slug` nunca se toca — es el contrato con `dispatch_notification()`).
- `dashboard/services/admin_orchestrators.py`: `NotificationAdminOrchestrator`.
- `dashboard/api/views.py` + `urls.py`: `AdminNotificationTemplateViewSet` (list + partial_update)
  y `AdminNotificationLogViewSet` (list, solo lectura) en `dashboard/notification-templates/` y
  `dashboard/notification-logs/`.

Frontend (nuevo):
- `frontend/src/modules/notifications/NotificationsAdminView.vue` — 2 tabs (Plantillas con edicion
  via `SintelOffcanvas`, Logs con filtros + paginacion), patron identico al resto del panel.
- Ruta `/panel/notificaciones` (`name: 'notifications-admin'`) + entrada en `Sidebar.vue`.

### Fase de correccion 3 — Vista centralizada de pagos — severidad BAJA — HECHO

Backend (nuevo):
- `payment/online/api/serializers.py`: `TransactionSerializer` extendido con
  `order`/`rental_request`/`payment_method_type` (aditivo — el ViewSet que lo usa es
  `viewsets.ViewSet`, no `ModelViewSet`, sin riesgo en validacion de escritura).
- `payment/services/selectors.py` (nuevo): `PaymentAdminSelector` — 3 metodos separados
  (`list_wompi_transactions`, `list_nequi_transactions`, `list_cod_transactions`) porque los 3
  modelos no comparten forma de datos (cents vs Decimal, distintos estados).
- `dashboard/services/admin_orchestrators.py`: `PaymentAdminOrchestrator`.
- `dashboard/api/views.py` + `urls.py`: `AdminPaymentViewSet` en `dashboard/payment-transactions/`
  (Wompi, list default), `.../nequi/` y `.../cod/` (actions).

Frontend (nuevo):
- `frontend/src/modules/payment/PaymentTransactionsAdminView.vue` — 3 tabs (Wompi/Nequi/COD), cada
  uno con filtro de estado + tabla + paginacion (markup inline igual que el resto del panel — no
  se introdujo ningun patron de render-function `h()`, se descarto un intento inicial que lo usaba
  por no ser consistente con el resto del codebase).
- Ruta `/panel/pagos` (`name: 'payment-transactions'`) + entrada en `Sidebar.vue`.

### Verificacion

- `docker exec ecommerce_sintel_django python manage.py check` — OK (solo el warning
  pre-existente no relacionado de `cart.Cart.user`).
- `docker exec ecommerce_sintel_frontend npx vite build --mode production` — OK tras corregir un
  bug real detectado por el build (interpolacion `{{ }}` mal escapada en un `<div class="form-text">`
  de `NotificationsAdminView.vue`, corregida con entidades HTML `&#123;&#123;`).

### Limpieza de deuda tecnica adicional — HECHO (turno siguiente, 2026-07-11)

El usuario pidio explicitamente "aplica correcciones segun deuda tecnica". Se confirmo (pregunta
directa, el sistema bloqueo el borrado hasta nombrar los archivos exactos) y se elimino:
- `frontend/src/components/ui/landing/TrustSection.vue`
- `frontend/src/components/ui/landing/TrustCard.vue`

Verificado antes de borrar: ningun archivo del proyecto los importaba; `HomeView.vue` usa
`@/renderers/SectionRenderer.vue` para renderizar `home_cards`/`card_groups` (el feature que
`TrustSection` cubria fue reemplazado por un sistema de layout mas flexible, no es un gap de
"contenido no renderizado" sino codigo genuinamente obsoleto). `vite build --mode production`
limpio despues del borrado.

**Deuda tecnica restante, NO tocada** (se pregunto explicitamente y el usuario opto por dejarla
para otra sesion): los 9 items de la tabla en
[architecture_audit.md](architecture_audit.md#deuda-tecnica-conocida-no-inventar-que-esta-resuelta)
(Vitest, Playwright, regresion visual, auditoria WCAG, dark mode, offline/retry, patron
vee-validate/yup, exportacion/acciones masivas en tablas, Suspense/Error Boundaries, indexacion RAG
de `ai_skills/drf/`) — son decisiones de alcance/tooling, no bugs de sincronizacion.
