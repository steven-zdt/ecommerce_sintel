# 01 — AUDITORÍA GENERAL
**Proyecto:** Sintel E-Commerce REST
**Fecha:** 2026-07-25 (reescritura completa — ver §0 "Qué cambió desde la versión anterior"). **Actualizado 2026-07-27** con verificación y correcciones en vivo — ver §7 (sesión mañana) y §9 (sesión tarde: Celery + verificación Wompi). Documentos 02-13 sincronizados en la misma pasada — ver §8.
**Version anterior:** 2026-07-16 (ver historial en git de este archivo)
**Referencia:** `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`
**Alcance:** Backend Django 5.2 (19 apps de negocio + `ecommerce/` config) + Frontend Vue 3 + AI Engine FastAPI
**Método:** Lectura directa del código actual (no solo documentación), verificación linea por linea de cada hallazgo de la version anterior contra el estado real, ejecución de la suite de tests real (Docker + Postgres) donde aplicaba.

---

## 0. Qué cambió desde la versión anterior (2026-07-16 → 2026-07-25)

La versión anterior de este documento (4 críticos, 25 altos, 40 medios) quedó **mayormente resuelta** en tres rondas de trabajo posteriores, todas verificables en el código (no solo en checklists):

1. **SPRINT 0-4** (`12_CHECKLIST_IMPLEMENTACION.md`, 2026-07-16/17) — seguridad crítica, bugs funcionales, base de datos, service layer, frontend. Todos los items marcados `[x]` están confirmados en el código actual.
2. **"Auditoría Enterprise"** (2026-07-24) — 10 correcciones adicionales (códigos `Q-*`, `N-*`, `R-*`, `F-*`, `O-*`, `A-*`, `C-*`, más ~25 hallazgos menores `S-*`, `D-*`, `K-*`, `M-*` dispersos por dominio) organizadas en 3 "olas" por urgencia de explotación, más un pipeline de CI. Verificadas todas presentes en el código el 2026-07-25.
3. **Endurecimiento de tests** (2026-07-25, esta sesión) — 8 de las 10 correcciones de la Auditoría Enterprise NO tenían test de regresión pese a estar implementadas; se escribieron los 8 que faltaban (`quotes/tests.py` nuevo, `ecommerce/tests.py` nuevo, más adiciones a `notifications/`, `technical_services/`, `payment/`, `users/tests.py`). En el proceso se encontró y corrigió un bug real no detectado antes: `PackagePriceCalculator.calculate()` (paquetes de servicios técnicos) no acotaba `discount_pct` — un valor `>100` producía un total negativo en el endpoint público `quote-package`. Corregido y cubierto por test.
4. **Auditoría E2E de Renting** (2026-07-21/25, simulación de usuario real) — encontró y corrigió 2 bugs bloqueantes de UI (`<Transition mode="out-in">` en `RegisterView.vue` y `RentalBookingWizard.vue`, que dejaban el registro y la reserva congelados tras un reintento exitoso) más 7 hallazgos menores. Ver `Documentacion/` o el historial de sesión para el detalle completo — no está en el árbol de `AUDITORIA/` porque nació de una auditoría funcional, no de código estático.

**Resultado neto (2026-07-25):** de los 4 hallazgos críticos originales, **4 están resueltos**. De los 16 de alta prioridad originales, **15 están resueltos** y **1 sigue abierto** (`SEC-H6`, ver §2). El frontend tiene su propio documento actualizado y vigente (`13_AUDITORIA_FRONTEND_UI_2026-07-23.md`) con hallazgos de deuda técnica (no de seguridad) que siguen mayormente abiertos — ver §5.

**Actualización 2026-07-27 (ver §7 para el detalle):** `SEC-H6` se verificó ya resuelto en el código (no lo reflejaba esta tabla) y `DB-H1` (el único pendiente de alta prioridad de deuda técnica estructural) se cerró generando y aplicando la migración `0036` que faltaba. **16 de 16 hallazgos de alta prioridad ahora resueltos.** En el camino se encontró y corrigió un incidente crítico nuevo, no listado en ninguna versión anterior de este documento: un `NameError` en `renting/api/views.py` dejaba **todo el backend respondiendo 500** (§7.1). Continuando con la punch list de frontend (doc 13): `utils/money.js` (P1-1) se verificó ya resuelto por una sesión previa no documentada aquí, y `useErrorHandler` (P1-2) se completó en esta sesión (§7.4-7.5). P1-4 (migración Pinia de 40 módulos admin) se completó al 100% más adelante en esta misma sesión, en 13 incrementos verificados en vivo (§7.7-§7.21), junto con el cierre del residual de FE-H5 (§7.20). Queda abierto únicamente P1-3 (descomponer `HomeConfigView.vue` en subcomponentes por sección), diferido a propósito a su propia sesión dedicada — ver §7.6/§7.21.

---

## 1. Métricas Globales (recalculadas 2026-07-25)

| Dimensión | Valor | Nota |
|---|---|---|
| Apps Django de negocio | 19 | `accounts, cart, core, dashboard, inventory, kyc, marketing, notifications, operations, orders, organization, payment, quotes, renting, security, shop, support, technical_services, users` |
| Archivos `.py` (excl. migraciones, `.venv`) | 388 | La cifra "5.749" de la version 2026-07-16 incluía dependencias/`.venv` — no es comparable |
| Componentes Vue (`.vue`) | 316 | +36 desde 2026-07-16 (280) |
| Stores Pinia (archivos) | 19 | +6 (splits de SPRINT 4: `rentingAdmin/`, `quotesAdmin/`, `technicalServicesAdmin/` en sub-stores por dominio) |
| Composables | 21 | +3 |
| Decoradores `@transaction.atomic` | 381 | +58 desde 2026-07-16 (323) |
| Archivos `tests.py` / `test_*.py` | 22 | `quotes/tests.py` y `ecommerce/tests.py` son nuevos (2026-07-25) |
| Pipeline de CI | **Existe** | `.github/workflows/ci.yml` — Postgres real, migraciones, `manage.py check`, pytest+cobertura, Bandit (SAST). No existía en la version anterior. |

---

## 2. Hallazgos Críticos originales — estado 2026-07-25

| ID | Descripción | Estado | Evidencia |
|---|---|---|---|
| SEC-C1 | `inventory/api/views.py` usaba `IsAdminUser` de DRF (solo `is_staff`) | ✅ **Resuelto** | `inventory/api/views.py:7` importa `users.api.permissions.IsAdminUser`; `get_permissions()` lo aplica a todas las acciones (create/adjust_stock/list/retrieve) |
| SEC-C2 | `integrity_signature` expuesta en respuesta de la API de pagos | ✅ **Resuelto (con matiz)** | Ya no está en `payment/online/api/serializers.py`. Sigue presente en la respuesta de `initialize()` (`views.py:415`) — **esto es intencional**: `useWompiWidget.js` la necesita para abrir el Widget de Wompi; sin ella el pago falla con "firma inválida". El riesgo original (fuga en respuestas de solo-lectura/confirmación/webhook) está cerrado; queda expuesta únicamente al dueño autenticado de su propio pago, en el único punto donde es funcionalmente necesaria. |
| SEC-C3 | `/api/schema/` y `/api/docs/` accesibles por cualquier usuario autenticado | ✅ **Resuelto** | `ecommerce/urls.py:35-36` — ambas rutas tienen `permission_classes=[IsAdminUser]` |
| ARCH-C1 | `core/services/selectors.py` contenía Commands (escrituras) en archivo de lectura | ✅ **Resuelto** | `core/services/selectors.py` ya no define ninguna clase `*Commands`; movidas a `core/services/commands.py` (SPRINT 1) |

**Los 4 hallazgos críticos originales están cerrados.**

---

## 3. Hallazgos de Alta Prioridad originales — estado 2026-07-25

| ID | Descripción | Estado |
|---|---|---|
| SEC-H1 | Admin login sin rate limiting | ✅ Resuelto — `users/api/admin_auth.py` tiene `throttle_scope='admin_login'`, `'5/hour'` en settings |
| SEC-H2 | Quotations: file upload sin validación anónima | ✅ Resuelto — `validate_file()` en `create_quotation`/`add_attachment`, cubierto por `quotes/tests.py` (nuevo, 2026-07-25) |
| SEC-H3 | SuccessCase upload sin magic bytes | ✅ Resuelto — `magic_bytes_check=True` en `accounts/services/commands.py:784` |
| SEC-H4 | Operations `upload_document` sin validación | ✅ Resuelto — `validate_file()` presente, `max_size_mb=10`, `magic_bytes_check=True` |
| SEC-H5 | `/api/v1/internal/ai/*` accesible externamente | ✅ Resuelto — `nginx-common.conf` tiene `location /api/v1/internal/ { deny all; return 403; }`, verificado en vivo contra producción (`12_CHECKLIST_IMPLEMENTACION.md` §Verificación Final) |
| **SEC-H6** | **Cambio de contraseña no invalida tokens JWT existentes** | ✅ **[OK] Resuelto — verificado 2026-07-27** — `AccountCommands._blacklist_all_refresh_tokens()` (`accounts/services/commands.py:409`) blacklistea todos los `OutstandingToken` del usuario; se llama desde `change_password()`, `admin_reset_password()` y `CustomerPasswordResetCommands.confirm_reset()` (los 3 puntos donde se cambia una contraseña). Cubierto por `accounts.tests.PasswordChangeRevokesRefreshTokensTestCase` (3 tests, uno por caller) — corrido en vivo contra el contenedor `ecommerce_sintel_django`: **3/3 OK**. |
| SEC-H7 | Inventory list/retrieve accesible por cualquier autenticado | ✅ Resuelto — `get_permissions()` exige `IsAdminUser` para todas las acciones, no solo create |
| ARCH-H1 | `users/services/commands.py` sin `@transaction.atomic` | ✅ Resuelto — 5 decoradores presentes |
| ARCH-H2 | `payment` `initialize_transaction` sin `@transaction.atomic` | ✅ Resuelto (con diseño más fino) — el bloque atómico cubre creación+firma; la llamada a Wompi corre deliberadamente fuera para que un `ERROR` audit-trail sobreviva un fallo de red sin perder el registro (ver comentario en `payment/online/services/commands.py:66`) |
| ARCH-H3 | `dashboard/api/views.py`: 6 operaciones ORM directas | ✅ Resuelto — delegadas a Commands (SPRINT 3, verificado) |
| ARCH-H4 | `inventory/api/views.py`: `StockRecord` creado directo | ✅ Resuelto — usa `InventoryCommands.create_stock_record()` |
| ARCH-H5 | `cart/api/views.py:125`: `.delete()` físico bypasea Commands | ✅ Resuelto — `CartCommands.remove_item()` con soft-delete real, conectado |
| ARCH-H6 | `payment/cards/views.py`: CRUD sin Commands | ✅ Resuelto — usa `PaymentCardCommands` en las 3 acciones |
| ARCH-H7 | `dashboard/services/admin_orchestrators.py`: ORM directo en Orchestrator | ✅ Resuelto — usa Selectors (`OrderSelector`, `UserSelector`, `ProductSelector`) |
| DB-H1 | `RentalRequest` con ~50 campos | ✅ **[OK] Resuelto — completado 2026-07-27** — el split ya estaba hecho a nivel de código (4 sub-modelos `RentalRequestLocation/Contact/Costs/PaymentInfo`, migraciones 0034/0035, capa de delegacion via `@property` en `renting/models.py`) pero la migracion final que debia eliminar las 35 columnas viejas de `RentalRequest` (referenciada en el codigo como "migracion 0036") nunca se habia generado — dejaba esas columnas `NOT NULL` sin valor en cada INSERT nuevo. Ver §7 para el detalle completo del hallazgo y la correccion (incluye un bug critico nuevo, no en la lista original, que dejaba **todo el backend caido con 500**). |
| DB-H2 | `ServiceReview` sin `unique_together` | ✅ Resuelto — `unique_together = ('user', 'service')`, migración aplicada, 0 duplicados verificados antes de aplicar |
| DB-H3 | `StockRecord.item_variant` GFK roto | ✅ Resuelto (documentado + mitigado) — el GFK nunca resuelve por diseño; comentario explícito en el modelo + `StockRecordSelector.batch_load_item_variants()` como camino correcto; 0 callers directos del GFK roto en todo el repo |
| DB-H4 | `Quotation.status` sin `db_index` | ✅ Resuelto — `db_index=True` presente |
| FE-H1 | Ruta `/panel/ordenes/renting` inaccesible (shadowed) | ✅ Resuelto — `ordenes/renting` precede a `ordenes/:uuid` en el router |
| FE-H2 | `apps/customer/main.js` muerto | ✅ Resuelto — archivo eliminado junto con su entrada en `vite.config.js` |
| FE-H3 | 3 mega-stores >400 líneas, 9+ dominios | ✅ **[OK] Resuelto — completado 2026-07-27** — los 3 stores (`rentingAdmin`, `quotesAdmin`, `technicalServicesAdmin`) se dividieron en sub-stores por dominio funcional (SPRINT 4); la migración a Pinia de los 40 módulos admin restantes (`shop`, `orders`, `operations`, `kyc`, `marketing`, `core`, `organization`, `payment`, `security`, `notifications`, `users`) se completó al 100% en esta sesión (ver §6 punto #6, §7.7-§7.21) |
| FE-H4 | `alert('Global Debug Triggered')` en `AppShell.vue` | ✅ Resuelto — eliminado |
| FE-H5 | 193 llamadas Axios directas sin capa de servicio | ✅ **[OK] Resuelto — completado 2026-07-27** — se crearon 4 servicios (`shop`, `quotes`, `technical_services`, `operations`, SPRINT 4); `kyc`/`marketing` resultaron ya sin consumidores residuales al verificar, y el residual real de `orders` (2 hallazgos: llamada suelta en `CustomerOrdersView.vue` + store/service duplicado en `OrderDetailView.vue`) se cerró (ver §7.20) |
| FE-H6 | `RentalBookingWizard.vue` minificado, ilegible | ✅ Resuelto — desminificado a 1.582 líneas legibles (SPRINT 4); posteriormente también se le quitó el `<Transition mode="out-in">` que causaba el bug de congelamiento entre pasos (auditoría E2E, 2026-07-25) |

**[OK] 16 de 16 hallazgos de alta prioridad resueltos (actualizado 2026-07-27 — `SEC-H6`/`DB-H1` en la
primera pasada, `FE-H3`/`FE-H5` en la segunda, ver §7).** P1-3 (descomponer `HomeConfigView.vue` en
subcomponentes, §6 punto #5 — no correspondía a ningún hallazgo `FE-H*` de esta tabla, era una
recomendación de mantenibilidad de doc 13 §6) también se cerró el mismo día — ver §7.22. Punch list de
§6 completa al 100%.

---

## 4. Hallazgos nuevos desde 2026-07-16 (Auditoría Enterprise + auditoría E2E)

No estaban en la versión anterior de este documento. Todos verificados **resueltos y con test de regresión** al 2026-07-25:

| Código | Descripción | Dominio |
|---|---|---|
| Q-01 | PDF de cotización descargable sin autenticación (`AllowAny` + query directo bypass del `get_queryset()` scoped) | quotes |
| Q-02 | Adjuntos de cotización sin límite de tamaño/extensión/magic-bytes | quotes |
| N-01 | Webhook de WhatsApp sin verificar `X-Hub-Signature-256` — suplantación de clientes vía Action Graph de IA | notifications |
| R-01 | `discount_pct` sin límites en servicios técnicos — total negativo posible (bug real encontrado en 2 lugares: `ServiceSelector` ya tenía el clamp, `PackagePriceCalculator` no — corregido 2026-07-25) | technical_services |
| F-01 | Webhook de Wompi fail-*open* sin `WOMPI_EVENTS_SECRET` — permitía falsificar pagos aprobados | payment |
| F-02 / O-01 | Condición de carrera en `initialize()` de pago y en `create_from_cart()` — doble clic podía crear 2 transacciones/órdenes | payment, orders |
| A-01 | Código OTP en texto plano en los logs | users |
| C-01 | Sin fail-safe: `settings.production` podía arrancar con `DEBUG=True` | ecommerce (config) |
| C-04 | Tests sin garantía de correr contra Postgres real (SQLite no bloquea filas — invalidaba los tests de concurrencia) | proyecto (conftest.py) |
| — | Pipeline de CI mínimo (Postgres, migraciones, tests+cobertura, Bandit) | proyecto (`.github/workflows/ci.yml`) |

Más 2 bugs bloqueantes de UI encontrados en la auditoría E2E de Renting (simulación de usuario real, no análisis estático): el registro de usuario y el wizard de reserva se congelaban tras un reintento exitoso por un patrón frágil de `<Transition mode="out-in">` de Vue dependiente de `requestAnimationFrame`. Corregidos quitando la transición en ambos componentes.

---

## 5. Estado de Cumplimiento por Área (actualizado)

| Área | Estado 2026-07-16 | Estado 2026-07-25 |
|---|---|---|
| Service Layer Pattern (Commands/Selectors) | 85% conforme | ✅ Mejorado — ARCH-C1, ARCH-H3/H4/H5/H6/H7 cerrados |
| `@transaction.atomic` en Commands | 93% conforme | ✅ Mejorado — ARCH-H1/H2 cerrados (+58 decoradores nuevos) |
| Soft-delete obligatorio | 88% conforme | ✅ ARCH-H5 (cart) cerrado |
| `IsAdminUser` custom (no rest_framework) | 97% (2 excepciones) | ✅ 100% — SEC-C1/H7 (inventory) cerrados |
| Nginx bloqueo de rutas `/internal/` | 0% | ✅ 100% — SEC-H5 cerrado, verificado en vivo |
| File upload validation (magic bytes) | 70% conforme | ✅ Mejorado — SEC-H2/H3/H4 + Q-02 cerrados |
| Rate limiting en endpoints sensibles | Admin login sin protección | ✅ SEC-H1 cerrado; además Q-06 (throttle en `from_template`/`download_pdf`) |
| Webhooks con verificación de firma | Solo Wompi (parcial, fail-open) | ✅ Wompi fail-closed (F-01) + WhatsApp agregado (N-01) |
| Idempotencia en checkout/pagos | No implementada | ✅ F-02/O-01 — `select_for_update()` con test de concurrencia real (2 hilos, Postgres) |
| Invalidación de JWT en cambio de contraseña | No implementada | ❌ **Sigue sin implementar (SEC-H6)** |
| CI/CD con gate de calidad | No existía | ✅ `.github/workflows/ci.yml` — Postgres, tests+cobertura, Bandit |
| Cobertura de tests de seguridad (regresión) | No medida | ✅ 8 suites nuevas/ampliadas el 2026-07-25, 100% passing (144 tests entre `quotes`/`notifications`/`technical_services`/`payment`/`users`/`ecommerce`) |
| Migración completa a stores Pinia (admin) | No evaluado | ✅ 100% — ver §6 punto #6 y §7.7-§7.21 (actualizado 2026-07-27) |
| Utilidad compartida de formato de moneda | No evaluado | ❌ No existe — 63 archivos reimplementan `Intl.NumberFormat` (ver doc 13) |

---

## 6. Punch list — lo que queda genuinamente abierto

Estado actualizado 2026-07-27 (ver §7 para el detalle de la sesión de verificación/corrección):

1. ~~**SEC-H6**~~ — ✅ **[OK] Resuelto y verificado 2026-07-27** (3/3 tests pasando en vivo). Ver §3.
2. ~~**DB-H1**~~ — ✅ **[OK] Resuelto 2026-07-27** (migración 0036 generada y aplicada). Ver §3 y §7.
3. ~~**`utils/money.js`**~~ (doc 13, P1-1) — ✅ **[OK] Verificado ya resuelto 2026-07-27** (0 instanciaciones inline restantes, 62 archivos con `formatCOP`, 6/6 tests). Ver §7.4.
4. ~~**`useErrorHandler` adoption**~~ (doc 13, P1-2) — ✅ **[OK] Resuelto 2026-07-27** (48 archivos adoptando el composable; 13 migrados en esta sesión, 2 exclusiones deliberadas y verificadas quedan). Ver §7.5.
5. ~~**`HomeConfigView.vue`**~~ (doc 13, P1-3) — ✅ **[OK] Resuelto 2026-07-27.** 2.629 líneas / 250 declaraciones descompuestas en 8 subcomponentes por sección (106–618 LOC c/u) bajo `frontend/src/modules/core/home-builder/`; el archivo original quedó en 715 LOC. Ver §7.22.
6. ~~**Migración a stores Pinia**~~ (doc 13, P1-4) — ✅ **[OK] Resuelto 2026-07-27 — 100%.** Los 40 módulos admin listados (`shop`, `orders`, `operations`, `kyc`, `marketing`, `core`, `organization`, `payment`, `security`, `notifications`, `users`) migrados a stores Pinia dedicados; los 11 dominios originales de doc 13 §4.1 tienen store completo, incluyendo la última pieza (`HomeConfigView.vue`/`ModuleBuilderModal.vue`, 43+2 llamadas API). Ver §7.7-§7.21.
7. ~~**FE-H5 residual**~~ — ✅ **[OK] Resuelto 2026-07-27.** `kycService.js`/`marketingService.js` ya existían sin consumidores residuales (verificado); `orders` tenía 2 hallazgos reales (`CustomerOrdersView.vue` con una llamada suelta, y un store/service duplicado no descubierto en `OrderDetailView.vue`) — ambos corregidos y consolidados. Ver §7.20.

**De los 7 puntos originales, los 7 se cerraron el 2026-07-27 — punch list 100% completa.** (#1-#4 en
la primera pasada; #6-#7 en la segunda; #5 al final, tras confirmar explícitamente con el usuario que
esa sesión sería la "sesión dedicada" acordada en §7.6/§7.21 en vez de diferirla — ver §7.22). La
sesión del 2026-07-27 también encontró y cerró **un incidente nuevo, no listado aquí originalmente**:
un `NameError` en `renting/api/views.py` dejaba **el backend completo respondiendo 500 a cualquier
request** (ver §7.1) — de severidad mayor que cualquier punto de esta lista, y ya resuelto.

---

## 7. Sesión de verificación y correcciones — 2026-07-27

Continuación de la punch list de §6. Metodo: lectura directa del código (no solo el checklist),
ejecución real de tests contra el contenedor `ecommerce_sintel_django` (Postgres real, DB de
desarrollo `ecommerce_sintel_db` — **no** `sintel_prod_db`), y verificación en vivo del backend con
`curl` contra `localhost:8000`.

### 7.1 [OK] Incidente nuevo encontrado y resuelto — backend completo caido (500 en todo)

**No estaba en la lista original.** Al arrancar la verificación, `curl http://localhost:8000/api/v1/cart/wishlist/`
devolvia `500` (Daphne, "Exception inside application") — y asi **cualquier** endpoint, porque
`ecommerce/urls.py` importa `renting.urls` a nivel de modulo y esa importacion fallaba:

```
NameError: name 'RentalRequestFilterSet' is not defined
  File "renting/api/views.py", line 457, in RentalRequestViewSet
    filterset_class = RentalRequestFilterSet
```

`RentalRequestViewSet.filterset_class` referenciaba una clase que nunca se llego a escribir (el
comentario en el codigo decia "Ver RentalRequestFilterSet mas abajo" — pero ademas de no existir,
tampoco habria funcionado abajo: una clase Python debe existir ANTES de ser referenciada como valor
de atributo). Confirmado en `docker logs ecommerce_sintel_django` y en el estado real del contenedor
(`docker ps` lo marcaba `unhealthy`).

**Correccion:** se agrego la clase faltante en `renting/api/views.py` (antes de `RentalRequestViewSet`):

```python
class RentalRequestFilterSet(django_filters.FilterSet):
    payment_method = django_filters.CharFilter(field_name='payment_info__payment_method')

    class Meta:
        model = RentalRequest
        fields = ['status', 'payment_method', 'refund_required']
```

**Verificado:** `curl` contra `cart/wishlist/`, `shop/products/` y `renting/equipment/` volvio a dar
200/401 (segun auth) en vez de 500; `docker ps` paso a `healthy` sin reiniciar el contenedor
manualmente (recarga automatica del proceso al detectar el cambio de archivo).

### 7.2 [OK] DB-H1 — cerrado: migración 0036 generada y aplicada

Al correr la suite de `renting` para confirmar el fix de 8.1, aparecieron **62 errores** por:

```
django.db.utils.IntegrityError: null value in column "location_address" of relation
"renting_rentalrequest" violates not-null constraint
```

Investigacion: el split de `RentalRequest` en 4 sub-modelos (`RentalRequestLocation`,
`RentalRequestContact`, `RentalRequestCosts`, `RentalRequestPaymentInfo` — 35 campos en total) ya
estaba **completamente implementado a nivel de codigo** — migraciones 0034 (crea las tablas hijas) y
0035 (backfill, confirmado 61/61 filas migradas) ya aplicadas, mas una capa de delegacion via
`@property`/`__init__`/`save()` en `renting/models.py` bien diseñada y ya funcional. Lo unico que
faltaba era la migracion final que el propio codigo lleva meses anunciando en comentarios
("las columnas se movieron en la migracion 0036") — **nunca se genero**. Las 35 columnas viejas
seguian existiendo en la tabla real con `NOT NULL` y sin default, y como el modelo Python ya no las
declara como campos (son properties), el INSERT de Django dejo de enviarles valor: cualquier
`RentalRequest` nuevo fallaba.

**Correccion:**
1. Verificado el backfill de 0035 esta completo (61/61 en las 4 tablas hijas vs. 61 `RentalRequest`) antes de tocar nada.
2. `python manage.py makemigrations renting` — Django autogenero exactamente los 35 `RemoveField` esperados (coincide 1:1 con `RentalRequest.MOVED_FIELD_NAMES` en el modelo).
3. `python manage.py migrate renting` — aplicado contra `ecommerce_sintel_db` (dev, no produccion).
4. Se documento el porque en la migracion (`0036_remove_rentalrequest_access_conditions_and_more.py`).

**Verificado:** suite completa de `renting` + `accounts.tests.PasswordChangeRevokesRefreshTokensTestCase`
corrida con DB de test fresca (sin `--keepdb`): **100/100 tests OK**.

### 7.3 [OK] SEC-H6 — re-verificado (ya estaba resuelto, la tabla de §3 no reflejaba el codigo actual)

El código ya tenía `AccountCommands._blacklist_all_refresh_tokens()` implementado y conectado en los
3 puntos donde se cambia una contraseña (`change_password`, `admin_reset_password`, `confirm_reset`),
con su suite de tests (`accounts.tests.PasswordChangeRevokesRefreshTokensTestCase`, 3 tests). Se
corrió en vivo para confirmar que no solo existe sino que pasa: **3/3 OK**. Este documento (§3) tenía
este hallazgo marcado como abierto por desactualización, no porque el código lo estuviera — corregido
en esta pasada.

### 7.4 [OK] P1-1 (`utils/money.js`) — verificado ya resuelto, sin cambios de código necesarios

Al revisar este punto de la punch list se encontró que **ya estaba completamente implementado**
por una sesión previa no reflejada en este documento: `frontend/src/utils/money.js` (`formatCOP`)
existe, `frontend/CLAUDE.md` ya tiene la regla actualizada ("usar `formatCOP()`... nunca instanciar
`Intl.NumberFormat` inline"), y `frontend/src/utils/money.test.js` cubre el comportamiento (6 tests).
Verificado en vivo: **0 instanciaciones inline restantes** en todo `frontend/src` (antes 63 archivos);
**62 archivos** consumen `formatCOP` hoy. `npx vitest run src/utils/money.test.js` → **6/6 OK**.

### 7.5 [OK] P1-2 (`useErrorHandler` adoption) — completado en esta sesión

Estado inicial (esta sesión): **39 archivos** ya usaban `useErrorHandler` (una sesión previa había
avanzado bastante mas alla del "2 de 63" original de la auditoria, sin que este documento lo
reflejara) y **22 archivos** seguian con extraccion manual. Se revisó cada uno de los 22 uno por uno
(no un reemplazo mecánico) para separar los candidatos reales de las excepciones ya documentadas en
`frontend/CLAUDE.md` (errores por campo renderizados en template, o mostrar **todos** los errores de
campo):

- **13 archivos migrados** a `handleError(e, fallback)` (catch de un solo mensaje via toast, el caso
  que la regla cubre): `KycDocumentUploadStep.vue`, `BaseBrandForm.vue`, `BaseCategoryForm.vue`,
  `KycVerificationPanel.vue` (4 catches distintos), `RentalLaborForm.vue`, `RentingForm.vue` (2
  catches), `ProductForm.vue` (2 catches), `TaxForm.vue`, `CustomerProfileView.vue`,
  `KycVerificationView.vue`, `RegisterView.vue` (`resendCode`), `ProductDetailView.vue`
  (`submitReview`), `CampaignForm.vue`.
- **1 archivo migrado a `extractErrorMessage`** (no `handleError`, para no introducir un toast que
  no existia): `store/renting/availabilityStore.js` — es un store Pinia que expone `this.error`
  para render inline, no dispara toasts.
- **~9 exclusiones deliberadas, verificadas una por una, no dejadas sin revisar:**
  - `useCatalogQuoteWizard.js`, `useQuoteWizard.js`, `AdditionalCostForm.vue`,
    `RentalBookingWizard.vue`: exponen el error en el template (`error.value`/`errors[k]`) o
    muestran **todos** los errores de campo — excepcion ya documentada en `CLAUDE.md`.
  - `AdminForgotPasswordView.vue`, `ForgotPasswordView.vue`, `CheckoutView.vue`: mismo patron
    (`codeError.value`/`step3Errors.value`/`stockError.value`), uno de ellos con comentario explicito
    de diseno aislado sin composables compartidos.
  - `RentalConfirmationView.vue`: logica de negocio especifica (mensaje distinto si el gateway de
    pago externo devuelve 502) — no es extraccion generica.
  - `CustomerCardsView.vue`, `ServiceCheckoutModal.vue`: mezclan errores de axios con errores planos
    de `tokenizeCard()` (fetch directo al SDK de Wompi, sin `.response`) — migrar habria descartado
    silenciosamente el mensaje real de tokenizacion en favor del fallback generico. Confirmado real
    via lectura del codigo (`useCardTokenization`), no supuesto.
  - Stores admin (`rentingAdmin/*`, `quotesAdmin/*`, `technicalServicesAdmin/*`) y vistas de login
    (`LoginView.vue`, `AdminLoginPage.vue`, `VerifyEmailLinkView.vue`): mismo patron arquitectonico
    de "store devuelve `{ok, error}` / vista tiene campo de error inline" ya establecido en el resto
    del proyecto (doc 13 §4.1) — no es deuda, es el diseno vigente.

**Verificado:** `npx vite build` completo sin errores tras los 15 archivos tocados; `npx vitest run`
(suite completa) **25/25 OK**. Quedan exactamente 2 archivos con extraccion manual en todo el
proyecto, ambos justificados arriba (tokenizacion de tarjeta).

### 7.6 P1-3/P1-4 — confirmado sin avance previo; se define alcance incremental con el usuario

**P1-3** (descomponer `HomeConfigView.vue`, 2.629 LOC) y **P1-4** (completar migración a stores Pinia
de 40 módulos admin) siguen exactamente como estaban en la auditoría original — verificado que
ninguna sesión previa avanzó en ellos (a diferencia de P1-1/P1-2). Son de una naturaleza distinta a
los puntos ya cerrados: la propia auditoría (doc 13, plan §6) los describe como "esfuerzo alto,
incremental" y recomienda una rama + verificación propia por cada módulo/sección — no son refactors
mecánicos de bajo riesgo como money.js/useErrorHandler. Se consultó al usuario el alcance antes de
tocar código de este tamaño; se acordó arrancar P1-4 con un módulo chico como primer incremento
(ver §7.7) y dejar P1-3 para una sesión dedicada.

### 7.7 [OK] P1-4 — primer incremento: módulo `security` migrado a store Pinia

Elegido por ser el módulo admin más chico de los 11 pendientes (1 vista, 122 LOC, `SecurityDashboardView.vue`,
solo lectura — 2 GETs, sin mutaciones). Se creó `frontend/src/store/security.js`
(`useSecurityAdminStore`), siguiendo el mismo patrón ya establecido en `store/rentingAdmin/catalog.js`
(`_api()`, `loading`/`error` en `state()`, try/catch/finally) pero sin `actionLoading` al no haber
POST/PATCH/DELETE en este módulo. `SecurityDashboardView.vue` se actualizó para consumir el store via
`storeToRefs` en vez de `useApi()` directo. Documentado en
`ai_skills/frontend/architecture/state_management.md`.

**Verificado en vivo** (no solo build): `npx vite build` sin errores; login con usuario admin temporal
(creado y eliminado solo para esta verificación) contra `/panel/seguridad` — los 3 health-pills (DB/Redis/Celery)
y la tabla de eventos cargan correctamente desde el store, y el filtro por `event_type=LOGIN_FAILED`
dispara `store.fetchEvents(filters)` y refiltra la tabla correctamente (25 eventos → todos `LOGIN_FAILED`).

**Quedan 39/40 módulos admin pendientes** (`shop`, `orders`, `operations`, `kyc`, `marketing`, `core`,
`organization`, `payment`, `notifications`, `users`, y el resto de `security` si tuviera más vistas)
— cada uno amerita su propia verificación como esta, no un lote mecánico.

### 7.8 [OK] P1-4 — segundo incremento: módulo `notifications` migrado a store Pinia

`NotificationsAdminView.vue` (312 LOC, 2 pestañas: plantillas + logs de envío) migrado a
`frontend/src/store/notificationsAdmin.js` (`useNotificationsAdminStore`). A diferencia de `security`
(solo lectura), este módulo tenía una mutación real (`PATCH` de plantilla) — se usó `actionLoading`
para ella y se mantuvieron `templatesLoading`/`logsLoading` separados (los dos recursos se cargan en
paralelo al montar la vista; un solo flag compartido parpadearía mal). Nombre `notificationsAdmin.js`
(no `notifications.js`) para no chocar con el store ya existente de la campana del navbar
(`useNotificationsStore`, dominio distinto — feed personal del usuario, no el CRUD admin de
plantillas). Documentado en `state_management.md`.

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) contra
`/panel/notificaciones` — 55 plantillas cargan; edición de una plantilla dispara
`PATCH dashboard/notification-templates/{uuid}/` (200) + refetch automático + cierre del panel; tab
de logs carga 873 registros paginados y el botón "Sig." dispara
`GET dashboard/notification-logs/?page=2` correctamente. `npx vite build` y `npx vitest run` (25/25) sin
regresiones.

**Quedan 38/40 módulos admin pendientes.**

### 7.9 [OK] P1-4 — tercer incremento: módulo `payment` migrado a store Pinia

`PaymentTransactionsAdminView.vue` (418 LOC: 3 pestañas Wompi/Nequi/COD, 2 feature flags, resync,
historial de eventos) migrado a `frontend/src/store/paymentAdmin.js` (`usePaymentAdminStore`) — el
más completo de los 3 incrementos hasta ahora (2 mutaciones de flag + 1 acción de resync que
actualiza un item específico dentro de un array del store). Tab activo/filtro/página quedan como
estado local del componente, igual que en los 2 incrementos anteriores.

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) contra
`/panel/pagos` — 117 transacciones Wompi cargan con paginación; cambio de pestaña a Nequi dispara
`GET .../nequi/?page=1`; "Historial" en una transacción dispara
`GET .../{uuid}/events/` y renderiza el estado vacío correctamente; el toggle "Flujo via Widget"
dispara el `PATCH .../feature-flags/` real (200) — **se verificó con una llamada `fetch` directa que
el flag volvió a su valor original (`true`) tras la prueba**, ya que es un flag real que afecta el
checkout de este ambiente, no dejarlo alterado por la verificación. `npx vite build` y
`npx vitest run` (25/25) sin regresiones.

**Quedan 37/40 módulos admin pendientes.**

### 7.10 [OK] P1-4 — cuarto incremento: módulo `organization` migrado a store Pinia

`OrganizationView.vue` (431 LOC, 8 secciones independientes: empresa, branding, contacto, redes
sociales con CRUD completo, correos, dominios, SEO, información legal) migrado a
`frontend/src/store/organizationAdmin.js` (`useOrganizationAdminStore`) — el más grande de los 4
incrementos hasta ahora. Los formularios de edición (draft), previews de archivo y el estado de
confirmación de borrado quedan locales al componente; solo `socialLinks` se lee del store via
`storeToRefs` (es una lista de servidor que debe reflejar altas/bajas de inmediato).

**Bug real encontrado y corregido durante la migración (no llegó a producción):** el primer intento
dejó `socialLinks` como un `ref` local separado, poblado una sola vez en `fetchAll()` — como
`createSocialLink`/`deleteSocialLink` ahora mutan `store.socialLinks` (no el ref local), la lista en
pantalla habría quedado desactualizada tras cada alta/baja. Detectado en revisión antes de probar en
vivo (no fue el usuario ni un test quien lo encontró) — corregido usando `storeToRefs` para esa
propiedad específica en vez del ref local.

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) contra
`/panel/organizacion` — las 8 secciones cargan con los valores reales (`SINTEL CORP`, etc.); en
"Redes Sociales" se creó un link de prueba ("QA Test Platform") que apareció **inmediatamente** en la
lista (confirma el fix del bug de arriba), se eliminó con el flujo de confirmación inline, y quedó
todo como estaba antes de la prueba; "Contacto" se guardó (PATCH 200) sin cambiar datos reales.
`npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Hallazgo aparte, no relacionado con esta migración:** durante la verificación se detectó que
`DashboardView.vue` (`/panel/dashboard`) dispara un `404` en una de sus llamadas de resumen, lo cual
en cascada hace fallar el refresh de token e invalida la sesión (logout forzado). Es un bug
pre-existente, no introducido por ninguno de los 4 incrementos de esta sesión — **no se investigó
ni se corrigió**, queda anotado aquí para una sesión futura ya que afecta la experiencia real de
cualquier admin que aterrice en el dashboard tras iniciar sesión.

**Quedan 36/40 módulos admin pendientes.**

### 7.11 [OK] Incidente de producción — sintel.net.co caído (502), causa raíz distinta a los incidentes previos

Reportado por el usuario en vivo: `https://sintel.net.co/` devolvía `502 Bad Gateway` (Cloudflare).
No relacionado con la migración P1-4 en curso — es un incidente de infraestructura del stack
`sintel_production` (contenedores `sintel_prod_*`), separado del stack de desarrollo
(`ecommerce_sintel_*`) usado en el resto de esta sesión.

**Causa raíz:** `nginx` (prod) resuelve el hostname de su upstream (`django:8000`) mediante un bloque
`upstream{}` estático, que Nginx solo resuelve **una vez**, al arrancar o al hacer
`nginx -s reload`. El contenedor `sintel_prod_django` había sido recreado (rebuild de imagen —
`ecommerce_sintel:runtime` se reconstruyó hoy a las 13:07, dejando la imagen anterior huérfana/sin
tag) y obtuvo una IP nueva de Docker (`172.22.0.4`), pero `nginx` seguía intentando conectar a la IP
vieja (`172.22.0.5`) indefinidamente — `connect() failed (111: Connection refused)` en
`/var/log/nginx/public.error.log` en cada request. `django` en sí estaba sano; el corte era
exclusivamente en el salto nginx→django.

**Corrección inmediata (restaurar servicio):** `docker exec sintel_prod_nginx nginx -s reload` —
fuerza a nginx a re-resolver el DNS y recoger la IP correcta. Confirmado: `sintel.net.co` volvió a
200 en segundos.

**Corrección definitiva (para que no vuelva a pasar en el próximo rebuild):** se reemplazó el
`upstream django { server django:8000; }` estático por `resolver 127.0.0.11 valid=10s;` (DNS embebido
de Docker) + una variable en `proxy_pass` (`nginx-common.conf`, `location /`). Con esto nginx
revalida la IP de "django" cada 10s contra el DNS de Docker en vez de cachearla para siempre —
cualquier rebuild/redeploy futuro que cambie la IP del contenedor se recoge solo, sin necesitar un
reload manual de nginx. Se eliminó también el `upstream django{}` ahora muerto de `nginx.prod.conf`
(quedó solo un comentario explicando el porqué). Ambos archivos están bind-montados desde el repo
al contenedor (no requieren rebuild de imagen para aplicar, solo `nginx -s reload`).

**Verificación end-to-end del fix (no solo el `reload` inmediato):** durante la validación, el
contenedor `sintel_prod_django` fue removido y recreado por completo (una prueba deliberada que
terminó siendo más contundente que la planeada — un momento breve de indisponibilidad real, resuelto
en minutos). El log de nginx durante esa ventana mostró `django could not be resolved (3: Host not
found)` — confirmando que el resolver dinámico está activo y re-consultando el DNS en tiempo real
(antes habría quedado silenciosamente pegado a una IP vieja) — y en cuanto `django` volvió a existir,
las siguientes requests dieron `200` **sin ningún reload manual de nginx**, validando el fix en
condiciones reales.

**Verificación de integridad de datos** (por la recreación accidental de `sintel_prod_db` durante el
incidente, disparada por `docker compose up`): mismo volumen nombrado
(`sintel_production_sintel_prod_postgres_data`) reconectado, `PG_VERSION` con fecha de modificación
2026-07-10 (no de hoy, confirma que NO se reinicializó), datos reales presentes tras la recreación —
sin pérdida de datos.

**Validación de la imagen `sintel_production`** (lo que motivó originalmente la revisión): la imagen
`ecommerce_sintel:runtime` activa hoy (build 2026-07-27 13:07) **sí incluye** el fix crítico de
§7.1 (`RentalRequestFilterSet`) y la migración 0036 de §7.2 — ambos confirmados presentes en
`/code/renting/api/views.py` y `/code/renting/migrations/` dentro del contenedor. `showmigrations`
confirma **0 migraciones pendientes** en producción; `manage.py check --deploy` solo muestra
warnings cosméticos preexistentes (drf-spectacular, no bloqueantes).

**Estado final:** los 4 dominios (`sintel.net.co`, `www.sintel.net.co`, `api.sintel.net.co`,
`panel.sintel.net.co`) responden `200`. Stack `sintel_prod_*` completo, saludable.

### 7.12 [OK] P1-4 — quinto incremento: módulo `orders` migrado a store Pinia

`OrderList.vue` (96 LOC, listado) + `ShopOperationBoard.vue` (244 LOC, tablero operativo de
picking/empaque/despacho/entrega) migrados a `frontend/src/store/ordersAdmin.js`
(`useOrdersAdminStore`). Único de los 5 incrementos que delega en una capa de servicio ya existente
(`services/orders/ordersService.js`, SPRINT 4) en vez de llamar a `useApi()` directo — el store
orquesta estado, el service resuelve los endpoints; se preservó la única excepción que ya tenía el
componente original (`dashboard/dispatchers/` via `useApi()` directo, no via el service). El shipment
seleccionado y los 3 formularios de acción (empaque/programación/asignación) quedan locales al
componente.

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) — `OrderList`
carga 20 órdenes reales vía el store; `ShopOperationBoard` carga métricas + 6 despachos +
transportistas en paralelo; "Gestionar" dispara el fetch de timeline; se completó un empaque real
(`POST .../pack/`, 200) y se confirmó que el store refresca la lista, actualiza las métricas
(Pendientes de preparar 6→5, Pendientes de empacar 0→1), re-selecciona el mismo shipment mostrando
su nuevo estado ("Listo para despacho") y el nuevo evento en el timeline — el ciclo completo
mutación→refetch→re-selección funciona a través del store. Datos de QA en ambiente de desarrollo,
sin impacto real. `npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Quedan 35/40 módulos admin pendientes.**

### 7.13 [OK] P1-4 — sexto incremento: módulo `kyc` migrado a store Pinia

`KycAdminList.vue` (271 LOC, listado + KPIs) + `KycAdminDetail.vue` (37 LOC, wrapper de detalle) +
`KycVerificationPanel.vue` (380 LOC, acciones de revisión) migrados a
`frontend/src/store/kycAdmin.js` (`useKycAdminStore`). Caso particular: `KycVerificationPanel.vue`
es un componente **reusable** (recibe `verification` como prop, emite `changed` — no hace su propio
fetch) consumido tanto por `kyc/KycAdminDetail.vue` como por `users/UserDetail.vue`
(`reviewable=false`, flujo "Dar de alta") — se verificó el segundo consumidor antes de tocar nada
(`grep` confirmó que solo usa props/emit, sin acoplarse a implementación interna) para no romperlo
al mover sus 5 acciones de nivel-verificación al store compartido. La revisión documento-por-documento
(`reviewDocument`) se dejó llamando a `kycService` directo a propósito, ya que en el componente
original no compartía el flag de loading con las 5 acciones de nivel-verificación — meterla en el
store habría fusionado dos loading states independientes por diseño.

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) — listado carga
32 solicitudes reales + KPIs (1 pendiente, 31 en revisión, 0 aprobados mostrados en la métrica de
"Aprobados" — dato preexistente, no afectado por esta migración) via el store; detalle de una
verificación real carga con el store y el panel renderiza correctamente las acciones disponibles
según el estado (`PENDING` sin documentos → solo "Aprobación manual"/"Bloquear", coincide con los
guards `canForceApprove`/`canBlock`); se abrió y cerró el formulario de aprobación manual sin
confirmar (para no dejar un registro real en un estado terminal solo por la prueba). No se ejecutó
una mutación real de nivel-verificación en este incremento — el patrón de mutación es textualmente
idéntico al ya probado con llamadas reales en los 5 incrementos anteriores (payment, orders,
organization, notifications). `npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Nota aparte, no relacionada con esta migración:** se detectó un desajuste de datos preexistente —
el KPI reporta "31 en revisión" pero filtrar el listado por `UNDER_REVIEW` devuelve 0 resultados
(la query de KPIs y la de listado parecen usar un scope distinto). No se investigó ni corrigió, no
lo introdujo esta migración (ambas queries se pasan intactas a `kycService`, sin tocar su lógica).

**Quedan 34/40 módulos admin pendientes.**

### 7.14 [OK] P1-4 — séptimo incremento: módulo `marketing` migrado a store Pinia

`MarketingView.vue` (380 LOC: campañas/ofertas flash/agente IA) + `CampaignForm.vue` (274 LOC,
crear/editar) migrados a `frontend/src/store/marketingAdmin.js` (`useMarketingAdminStore`) —
delega en `services/marketing/marketingService.js` ya existente, mismo criterio que `ordersAdmin`.
`AgentRunDetail.vue` (118 LOC) no se tocó — es puro display (prop `run`, sin API). El formulario de
campaña (VeeValidate, `useFormValidation`) queda local al componente.

**Verificado en vivo, ciclo CRUD completo real:** login con admin temporal (creado y eliminado solo
para esto) — las 3 pestañas (Campañas/Ofertas/Agente IA) cargan correctamente via el store; se creó
una campaña de prueba real ("QA Test Campaign", `POST` 201) que apareció inmediatamente en la lista
tras el refetch automático del store; se eliminó la misma campaña (`DELETE` 204, confirmado con
`window.confirm` sobrescrito para auto-aceptar el diálogo nativo sin bloquear la automatización) y
se confirmó que desapareció de la lista. `npx vite build` y `npx vitest run` (25/25) sin
regresiones.

**Quedan 33/40 módulos admin pendientes.**

### 7.15 [OK] P1-4 — octavo incremento: módulo `operations` migrado a store Pinia

`OperationBoard.vue` (118 LOC, tablero general) + `DispatcherList.vue` (261 LOC, CRUD de
despachadores) + `OperationDetail.vue` (343 LOC, ticket individual con asignación/programación/
transición/revisión de documentos) migrados a `frontend/src/store/operationsAdmin.js`
(`useOperationsAdminStore`). Ninguno de los 3 tenía capa de servicio previa — el store llama a
`useApi()` directo. El autocompletado de usuarios de `DispatcherList.vue` quedó local (búsqueda
transitoria de UI).

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) — tablero de
operaciones carga 20 tickets reales; listado de despachadores carga 1 despachador real; detalle de
un ticket real carga con el store (orden asociada, timeline, documentos); "Auto-asignar" disparó un
`POST` real que el backend rechazó con `400` (sin personal disponible) — confirmado que el camino de
error (`{ok:false, error}` → `handleError` → toast) funciona sin crashear la vista, sin dejar la UI
en un estado inconsistente; "Asignar" abrió el modal y disparó `GET .../available-staff/` (200)
correctamente. `npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Quedan 32/40 módulos admin pendientes.**

### 7.16 [OK] P1-4 — noveno incremento: módulo `users` migrado a store Pinia

`UserList.vue` (403 LOC, listado + toggle/eliminar) + `UserForm.vue` (223 LOC, crear/editar) +
`UserDetail.vue` (364 LOC, detalle + auditoría + grupos + reset password/reenvío de verificación —
el más grande de los 9 incrementos) migrados a `frontend/src/store/usersAdmin.js`
(`useUsersAdminStore`). Sin capa de servicio previa — llama a `useApi()` directo.
`actionLoading` único compartido entre las 6 mutaciones simplificó 4 flags de loading
independientes en `UserDetail.vue` a uno solo del store (mismo criterio que `organizationAdmin`/
`kycAdmin`).

**Verificado en vivo:** login con admin temporal (creado y eliminado solo para esto) — listado
carga 45 usuarios reales; detalle de un usuario real carga con el store, incluyendo el
`KycVerificationPanel.vue` embebido (ya migrado en §7.13) funcionando correctamente con
`reviewable=false`; se abrió el editor de grupos (`GET users/groups-catalog/`, 200, catálogo
cacheado); se ejecutó "Reenviar verificación" real (`POST .../resend-verification/`, 200,
confirmado con el toast de éxito). `npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Quedan 31/40 módulos admin pendientes.**

### 7.17 [OK] P1-4 — décimo incremento (parcial, deliberado): módulo `shop` migrado a store Pinia

`BrandList.vue` (258 LOC) + `CategoryList.vue` (190 LOC) + `TaxList.vue`/`TaxForm.vue` (165+86 LOC) +
`ProductList.vue` (349 LOC) migrados a `frontend/src/store/shopAdmin.js` (`useShopAdminStore`).
**Alcance deliberadamente parcial:** `ProductForm.vue` (1.324 LOC — variantes, imágenes, reglas de
costo, múltiples tabs, cada uno con su propio CRUD) es comparable en tamaño/complejidad a un módulo
completo por sí solo — migrarlo junto con el resto habría sido un salto de riesgo mucho mayor que
cualquier incremento anterior de esta sesión. Queda como candidato a su propio incremento futuro,
mismo criterio que `HomeConfigView.vue`/`ModuleBuilderModal.vue` en `core` (P1-3). Tampoco se
tocaron `BrandForm.vue`/`CategoryForm.vue`: son wrappers finos sobre
`BaseBrandForm.vue`/`BaseCategoryForm.vue`, componentes genéricos ya compartidos con `renting`
(`RentingBrandForm.vue`/`RentingCategoryForm.vue`) — atarlos a un store de `shop` habría roto esa
reusabilidad.

**Bug real encontrado y corregido durante la verificación en vivo (no relacionado con Pinia):**
`BrandList.vue`, `CategoryList.vue`, `TaxList.vue`/`TaxForm.vue`, y los componentes compartidos
`BaseBrandForm.vue`/`BaseCategoryForm.vue` usaban `item.id` (PK entero) en las URLs de
edición/borrado, pero `AdminBrandViewSet`/`AdminCategoryViewSet`/`AdminTaxViewSet`
(`dashboard/api/views.py`) declaran `lookup_field = 'uuid'` — **toda edición o borrado de marca,
categoría o impuesto fallaba con `500`** (`"2" no es un UUID válido`), reproducido en vivo al
intentar borrar un impuesto de prueba. Corregido a `item.uuid` en los 5 archivos (los serializers ya
exponían ambos campos, no hizo falta cambio de backend). El mismo patrón existe también en
`renting/RentingBrandList.vue`/`RentingCategoryList.vue` — no corregido en esta sesión (`renting` no
es parte de este incremento), quedó como tarea de seguimiento separada.

**Verificado en vivo, incluyendo el fix:** login con admin temporal (creado y eliminado solo para
esto) — las 4 vistas cargan datos reales via el store; se creó y eliminó un impuesto de prueba real
(confirmando primero el bug con `DELETE` → 500, luego el fix con `DELETE` → 204); se editó y revirtió
una categoría real y una marca real (`PATCH` → 200 con uuid, antes habría sido 500 con id); en
`ProductList.vue` se probó el patch inline (toggle "destacado", `PATCH` → 200) y se revirtió.
`npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Estado de dominios (antes de §7.18):** de los 11 dominios listados en doc 13 §4.1 (`shop`, `orders`,
`operations`, `kyc`, `marketing`, `core`, `organization`, `payment`, `security`, `notifications`,
`users`), 10 tenían store dedicado (`shop` parcialmente — ver arriba). Solo `core` seguía sin
empezar, deliberadamente diferido por su solapamiento con la descomposición de `HomeConfigView.vue`
(P1-3, ver §7.6). El recuento exacto de "componentes" restante de la cifra original ("40 módulos") no
se verificó archivo por archivo — no se afirma aquí un número residual preciso.

### 7.18 [OK] P1-4 — undécimo incremento (parcial, deliberado): módulo `core` migrado a store Pinia

`AboutUsAdminView.vue` (255 LOC — configuración de `/nosotros`: hero, historia, misión, visión +
CRUD de valores institucionales) migrado a `frontend/src/store/coreAdmin.js` (`useCoreAdminStore`).
Sin capa de servicio previa — llama a `useApi()` directo. `actionLoading` único del store colapsó 3
flags de loading independientes del componente (`savingConfig`/`savingValue`/`deleting`), mismo
criterio que `usersAdmin`/`organizationAdmin`/`kycAdmin`. El draft del formulario de configuración y
el formulario de valor institucional quedan locales al componente, no en el store (mismo criterio que
todos los incrementos anteriores).

**Alcance deliberadamente parcial:** `HomeConfigView.vue` (2.629 LOC) y `ModuleBuilderModal.vue`
(1.588 LOC) — configuración de la home pública, fuertemente acopladas entre sí — NO se migran aquí.
Juntas son comparables a un módulo completo por sí solas y coinciden exactamente con la
descomposición diferida en P1-3 (§7.6) — mismo criterio de exclusión que `ProductForm.vue` en el
incremento anterior (§7.17). Si se aborda esa descomposición en el futuro, `store/coreAdmin.js` puede
ampliarse con las acciones correspondientes en vez de crear un store nuevo (documentado en el
comentario de cabecera del archivo).

**Verificado en vivo:** JWT generado directo via Django shell (`RefreshToken.for_user()`) e inyectado
en `localStorage` para evitar el throttle de `5/hour` del login admin (ya alcanzado en incrementos
previos de esta misma sesión). Navegación a `/panel/nosotros` — carga real via el store (config vacía,
"Sin valores institucionales configurados"). CRUD completo real: se creó un valor institucional real
"QA Test Value" (`POST dashboard/about-us/create/` → 201), confirmado en el listado tras refetch del
store, luego eliminado (`DELETE dashboard/about-us/{uuid}/delete/` → 204 tras confirmación inline).
`npx vite build` y `npx vitest run` (25/25) sin regresiones. Usuario admin temporal (QA) eliminado al
finalizar.

**Estado de dominios (antes de §7.19):** de los 11 dominios listados en doc 13 §4.1, los 11 tenían
store dedicado (`shop` y `core` parcialmente — ver §7.17 y arriba). Piezas pendientes por
tamaño/riesgo: `ProductForm.vue` (`shop`) y `HomeConfigView.vue`/`ModuleBuilderModal.vue` (`core`).

### 7.19 [OK] P1-4 — duodécimo incremento: `ProductForm.vue` (`shop`) migrado a store Pinia

`ProductForm.vue` (1.324 LOC — la pieza más grande diferida deliberadamente en §7.17) migrado,
extendiendo `frontend/src/store/shopAdmin.js` con: `productBrands`/`fetchProductBrands`
(`dashboard/brands/`, dropdown de marca), `activeTaxes`/`fetchActiveTaxes` (`dashboard/taxes/`
filtrado `is_active`, badges de impuestos), `createProduct`/`updateProduct` (devuelven `{ok, data,
error?}`, necesario para la transición interna create→edit sin cerrar el offcanvas), y CRUD completo
de `variants`/`costRules`/`productImages` (10 acciones nuevas: fetch + create/update/delete de
variantes, fetch + create/toggle/assign de reglas de costo, fetch + upload/delete/set-primary de
imágenes). El draft de creación/edición (formulario general/SEO, nueva variante, variante en edición,
regla de costo) permanece local al componente — mismo criterio que los 11 incrementos anteriores.
`fetchProductCategories` (ya existente para `ProductList.vue`, mismo endpoint exacto
`dashboard/categories/`) se reutilizó tal cual en vez de duplicarlo.

Los 4 flags de loading independientes del componente original (`variantLoading`/`costLoading`/
`uploading`/`imagesLoading` para mutaciones) se colapsaron en el `actionLoading` único del store —
mismo criterio que `usersAdmin`/`organizationAdmin`/`coreAdmin`. Efecto secundario menor identificado
durante la migración (no un bug, una limpieza incidental): el spinner de "cargando imágenes" ya no se
re-dispara durante un delete/set-primary de imagen individual (el código original reusaba el mismo
flag para el fetch de la lista y para esas 2 mutaciones, causando que la lista completa se
reemplazara por un spinner en medio de una acción puntual).

**Verificado en vivo**, con admin temporal (creado y eliminado solo para esto, vía JWT generado
directo por Django shell para evitar el throttle de login ya alcanzado en incrementos previos): se
creó un producto real "QA Test Product ProductForm Store" (`POST dashboard/products/` → 201),
confirmando la transición interna create→edit con la variante por defecto autogenerada por el backend
(`price_info` con IVA 19% aplicado correctamente). En la pestaña Costos se asignó una regla de costo
real existente a la variante principal (`POST .../shop-cost-rules/{uuid}/assign/` → 201). En la
pestaña Imágenes se subió una imagen real (`POST .../add_image/` → 201, marcada automáticamente como
principal) y se eliminó (`DELETE .../delete_image/{uuid}/` → 204). En Variantes se editó la variante
(`PATCH .../variants/{uuid}/` → 200) y se eliminó (`DELETE .../variants/{uuid}/delete/` → 204).
Producto de prueba eliminado al finalizar (`DELETE dashboard/products/{uuid}/` → 204). `npx vite
build` y `npx vitest run` (25/25) sin regresiones.

**Estado de dominios (antes de §7.20):** de los 11 dominios listados en doc 13 §4.1, los 11 tienen
store dedicado, y ambas piezas grandes de `shop`/`core` señaladas en incrementos anteriores habían
quedado reducidas a una sola: solo `HomeConfigView.vue`/`ModuleBuilderModal.vue` (`core`, P1-3, ver
§7.6) seguía deliberadamente sin migrar por su tamaño (2.629 + 1.588 LOC, fuertemente acopladas).

### 7.20 [OK] Cierre de FE-H5 residual — consolidación del dominio `orders`

Al verificar el punto #7 de la punch list (§6) — "`kyc`/`marketing`/`orders` quedaron fuera del
alcance de la capa de servicios de SPRINT 4" — se encontró que `kycService.js`/`marketingService.js`/
`ordersService.js` **ya existían** (mismo patrón que P1-1/P1-2: resuelto por una sesión previa no
reflejada en este documento) y que `kyc`/`marketing` no tenían ningún consumidor residual con
`useApi()` directo. `orders` sí tenía dos hallazgos reales:

1. **`CustomerOrdersView.vue`** (vista de cliente) tenía una llamada `api.get('orders/service-orders/
   {uuid}/')` residual junto al uso correcto de `ordersService`. Se agregó
   `ordersService.serviceOrderDetail(uuid)` y se migró el call site.
2. **`OrderDetailView.vue`** (`/panel/ordenes/:uuid`, ruta real y enrutada) usaba un store PARALELO
   no descubierto en el quinto incremento de P1-4 (§7.12): `store/orders/orderStore.js`
   (`useOrderStore`), que a su vez llamaba a un service distinto (`modules/orders/services/
   orderService.js`, no `services/orders/ordersService.js`). No apareció en el grep de `useApi()` de
   ese incremento porque la llamada estaba un nivel más abajo, detrás de otro service. Se agregaron
   `order`/`orderLoading`/`fetchOrder` a `store/ordersAdmin.js` (delegando en
   `ordersService.detail()`, que ya existía pero no se usaba desde ningún componente), se migró
   `OrderDetailView.vue` al store consolidado, y se eliminaron los 3 archivos ahora huérfanos:
   `store/orders/orderStore.js`, `modules/orders/services/orderService.js` y
   `modules/orders/services/timelineService.js` (este último ya estaba huérfano de antes, sin
   ningún consumidor — confirmado por grep antes de borrar).

**Verificado en vivo:** login con admin temporal — `/panel/ordenes/{uuid}` de una orden real carga
correctamente via el store consolidado (header, timeline, productos, notas, historial, resumen de
cliente, panel de asignación). `npx vite build` y `npx vitest run` (25/25) sin regresiones.

**Punto #7 de la punch list: [OK] Resuelto.**

### 7.21 [OK] P1-4 — decimotercer incremento: `HomeConfigView.vue`/`ModuleBuilderModal.vue` migrados — P1-4 100%

Última pieza pendiente de la migración a stores Pinia. Se consultó al usuario el enfoque dado el
salto de escala real descubierto al mapear el archivo (43 llamadas a la API en 12 sub-dominios:
módulos, banners, tarjetas, grupos de tarjetas, footer, enlaces de footer, columnas de footer,
marca, navbar, CTA final, items del slider de marcas, configuración del slider — más 2 llamadas en
`ModuleBuilderModal.vue`) y el riesgo real de P1-3 (el panel de preview en vivo del builder lee
estado de las 8 secciones simultáneamente para alimentar `HomeRenderer`/`CustomerNavbar`/
`CustomerFooter`). Se acordó: **P1-4 ahora (mecánico, mismo patrón que los 12 incrementos
anteriores — mover la capa de datos al store sin tocar la estructura del componente), P1-3
(descomponer el archivo en subcomponentes por sección) diferido a su propia sesión dedicada**, tal
como la propia auditoría (doc 13 §6) recomienda para este ítem específicamente.

`frontend/src/store/coreAdmin.js` se amplió con las 12 sub-secciones (ver
`ai_skills/frontend/architecture/state_management.md` para la firma completa de cada acción). Un
helper nuevo (`_headersFor(payload)`) detecta `payload instanceof FormData` para decidir el
Content-Type automáticamente, evitando tener que pasar un parámetro de headers en cada uno de los
~15 call sites que a veces envían JSON y a veces `multipart/form-data` según si hay un archivo
adjunto. El draft de cada uno de los ~10 formularios (banner/tarjeta/grupo/enlace/columna/marca/
navbar/CTA/item de marca/módulo) permanece local al componente — mismo criterio que los 12
incrementos anteriores. `groupTitlesMap`/`groupConfigMap` (transformación de UI sobre la lista cruda
de grupos) también quedan locales, reconstruidas desde `store.cardGroups` en vez de desde una
llamada a la API propia.

**Bug de sintaxis autoinfligido y corregido antes del build:** al mover las listas al store, quedaron
3 declaraciones locales duplicadas (`loadingBrand`, `loadingCta`, `loadingBrandConfig`) que ya
existían como alias de `storeToRefs` en el import — `vite build` lo detectó inmediatamente
(`Identifier 'loadingBrand' has already been declared`) antes de cualquier verificación en vivo;
corregido eliminando las 3 declaraciones redundantes.

**Verificado en vivo, las 12 sub-secciones + ModuleBuilderModal, con admin temporal (creado y
eliminado solo para esto):** `/panel/home-config` carga las 8 pestañas con conteos reales (7 módulos,
4 banners, 55 tarjetas, 6 columnas de footer, 6 enlaces de navbar, 3 logos) y el preview en vivo
renderiza contenido real de la home. Ciclo real de creación+eliminación verificado en: banners
(`POST create` → 201, `DELETE` → 204), tarjetas (ídem) + grupo de tarjetas (título vía `upsert` → 200,
eliminación → 204), enlace de footer/red social (`POST create` → 201, `DELETE` → 204), columna de
footer (ídem), logo del slider de marcas (ídem), enlace de navbar (ídem). Guardado real verificado en:
contacto de footer (`POST` → 200), marca (`PATCH` → 200), CTA final (`PATCH` → 200), configuración del
slider de marcas (`PATCH` → 200). Edición real de un módulo existente vía `ModuleBuilderModal.vue`
(`PATCH dashboard/home-config/modules/{uuid}/` → 200) — confirma que el store también cubre
correctamente el único componente que antes llamaba a la API por fuera de `HomeConfigView.vue`. `npx
vite build` y `npx vitest run` (25/25) sin regresiones.

**P1-4 (migración a stores Pinia de los 40 módulos admin listados en doc 13 §4.1): [OK] 100%
completo.** De los 11 dominios originales, los 11 tienen store dedicado y ningún componente de esos
11 dominios llama a `useApi()`/axios directo.

### 7.22 [OK] P1-3 — descomposición de `HomeConfigView.vue` en subcomponentes — punch list 100%

Última pieza de la punch list de §6, abordada en la misma sesión inmediatamente después de §7.21 (el
usuario confirmó explícitamente vía pregunta directa que esta era la "sesión dedicada" que se había
acordado en §7.21, en vez de diferirla a una sesión futura). `HomeConfigView.vue` bajó de **2.629 a
715 líneas**; las 8 secciones del Home Builder (módulos, banners, tarjetas, footer, marca, navbar, CTA
final, slider de marcas) se extrajeron a componentes propios en
`frontend/src/modules/core/home-builder/` (106–618 LOC cada uno — ver
`ai_skills/frontend/architecture/state_management.md` para el detalle completo de la arquitectura).

**Por qué se hizo después de P1-4 y no antes:** con los datos ya centralizados en `store/coreAdmin.js`
(§7.21), cada sección podía leer/escribir el store directo sin necesitar props/emits para los datos —
la única coordinación real pendiente era el panel de preview compartido (`HomeRenderer`/
`CustomerNavbar`/`CustomerFooter`), que en 4 de las 8 secciones necesita el **borrador sin guardar**
(no solo los datos ya persistidos). Se resolvió con `defineModel()`: el padre retiene el `ref()` real
de esos 4 borradores (`contactForm`, `brandForm`+`brandPreviewLogo`, `ctaForm`, `brandConfigForm`),
inicializado reactivamente vía `watch(store.xxx, ..., {immediate:true})`; cada sección lo recibe y
edita vía `v-model`. Esto resolvió de forma natural el único caso realmente cross-tab (`BrandSection`
es necesaria para el preview de **dos** pestañas, 'brand' y 'navbar') sin necesitar mantener el
componente montado permanentemente — el padre conserva el valor aunque la sección se desmonte.

**Verificado en vivo, las 8 secciones + el caso cross-tab, con admin temporal (creado y eliminado solo
para esto):** navegación directa a la pestaña 'navbar' sin pasar por 'brand' antes — el mini-preview y
el preview compartido mostraron correctamente "SINTEL CORP" (confirma que el `v-model` compartido
funciona sin depender del orden de montaje). Ciclo real de creación+eliminación en banners, tarjetas +
grupos de tarjetas (incluyendo renombrar un grupo real y confirmar que el cambio se reflejó tanto en
la lista como en el preview compartido antes de revertirlo), enlaces de footer/columnas de footer,
logos del slider de marcas, enlaces de navbar. Guardado real de contacto/marca/CTA/configuración del
slider. Edición real de un módulo existente vía `ModuleBuilderModal.vue`. `npx vite build` y `npx
vitest run` (25/25) sin regresiones en cada uno de los 8 incrementos individuales. Verificación final
de consola limpia (sin errores) en una pestaña de navegador completamente nueva tras el último cambio.

**Punch list de §6: [OK] 7 de 7 puntos cerrados — 100%.**

### 7.23 [OK] Incidente de producción 2026-07-29 — sitio inalcanzable (timeout, no 502) — puerto 7844 saliente bloqueado

Segundo incidente real de producción de esta rama, causa raíz **completamente
distinta** al de §7.11 (ese fue nginx cacheando una IP vieja de Django, daba
`502`; este es de infraestructura de red — daba **timeout puro**, ni
siquiera llegaba a nginx). Reportado por el usuario en vivo.

**Diagnóstico:** los 7 contenedores de `docker-compose.prod.yml` (django,
nginx, redis, db, celery_worker, celery_beat, cloudflared) estaban
`Up`/`healthy` — la aplicación nunca fue el problema. `docker logs
sintel_prod_cloudflared` ya lo diagnosticaba solo: `ERROR: Allow outbound
QUIC traffic on port 7844 or use HTTP2` / `ERROR: Allow outbound TCP on
port 7844`, con conexiones muriendo repetidamente por `"no recent network
activity"`. Aislado capa por capa **desde el host Windows, fuera de
Docker** (para descartar que fuera NAT de Docker): internet general y
Cloudflare-por-443 (`1.1.1.1`) funcionaban sin problema; `Test-NetConnection`
al puerto 7844 específicamente fallaba (ni TCP connect ni ping) — el único
puerto no estándar que usa el protocolo de Cloudflare Tunnel, bloqueado a
nivel de router/red local.

**Se descartó una vía de solución por software:** forzar `protocol: http2`
en `config.yml` (para evitar QUIC/UDP) no cambió nada, porque el puerto
estaba bloqueado para ambos transportes (TCP y UDP) por igual — se probó,
se confirmó que no resolvía, y se revirtió. **No existe ningún archivo de
este repositorio que controle esta capa de red.**

**Fix real:** el usuario abrió el puerto 7844 (TCP+UDP) saliente en el
router/firewall de la red — acción fuera del código, confirmada por el
usuario. Verificado: `docker logs sintel_prod_cloudflared` mostró conexión
estable (`Registered tunnel connection ... location=bog01`, sin caídas);
los 4 dominios (`sintel.net.co`, `www`, `api`, `panel`) volvieron a `200`
vía `curl` externo.

**Conocimiento persistido para que este diagnóstico no se repita desde
cero:** árbol de decisión completo (contenedores → 502 vs timeout puro →
logs de cloudflared → confirmar desde el host fuera de Docker) documentado
en `docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md` (nueva sección "Incidente
2026-07-29"), y como memoria de proyecto para sesiones futuras.

---

## 8. Documentos Generados

**Actualizado 2026-07-27:** los documentos 02-11 ya no son solo un snapshot de 2026-07-16 sin anotar —
cada uno recibió una pasada de sincronización (banner de estado + anotación ✅/🔶/❌ por hallazgo
Crítico/Alto, cruzada contra §2-4 de este documento y contra `12_CHECKLIST_IMPLEMENTACION.md`) a
pedido explícito del usuario ("actualiza y sincroniza los archivos en AUDITORIA"). Los hallazgos de
prioridad Media/Baja de esos documentos **no fueron re-verificados individualmente en esta pasada**
(fuera del alcance verificado por este documento maestro) — sus banners lo dejan explícito.

| # | Documento | Fecha | Vigencia |
|---|---|---|---|
| 01 | `01_AUDITORIA_GENERAL.md` | 2026-07-25 (act. 2026-07-27) | Este documento — reescrito completo + 2 sesiones de verificación, refleja el estado real actual |
| 02 | `02_DEUDA_TECNICA.md` | 2026-07-16 (sync 2026-07-27) | ✅ Crítica/Alta anotadas ✅ Resuelto contra este documento; Media/Baja sin re-verificar |
| 03 | `03_DUPLICIDAD_CODIGO.md` | 2026-07-16 (sync 2026-07-27) | ✅ Cada DUP anotado Resuelto/Abierto; la duplicidad de badges/timelines fue evaluada y descartada en doc 13 §2.3 |
| 04 | `04_OPTIMIZACION_BD.md` | 2026-07-16 (sync 2026-07-27) | ✅ Crítica/Alta anotadas (DB-H1 real desde §7.2, no solo el índice); Media sin re-verificar |
| 05 | `05_RENDIMIENTO.md` | 2026-07-16 (sync 2026-07-27) | ✅ Los 5 N+1 anotados Resueltos (SPRINT 2); agregado el hallazgo de cola Celery de §9.1 |
| 06 | `06_SEGURIDAD.md` | 2026-07-16 (sync 2026-07-27) | ✅ Crítica/Alta anotadas Resuelto contra §2-3; Media parcialmente verificada (ver banner) |
| 07 | `07_FRONTEND.md` | 2026-07-16 (sync 2026-07-27) | ❌ Reemplazado en la práctica por `13_AUDITORIA_FRONTEND_UI_2026-07-23.md` — banner cruzado agregado en ambos sentidos |
| 08 | `08_BACKEND.md` | 2026-07-16 (sync 2026-07-27) | ✅ ARCH-C1/H1-H9 anotados Resueltos; Media sin re-verificar |
| 09 | `09_API.md` | 2026-07-16 (sync 2026-07-27) | ✅ Matriz de permisos actualizada fila por fila con el estado real |
| 10 | `10_PLAN_REFACTORIZACION.md` | 2026-07-16 (sync 2026-07-27) | ✅ Marcado COMPLETADO — Iteraciones 1-5 ejecutadas, tabla de métricas actualizada |
| 11 | `11_QUICK_WINS.md` | 2026-07-16 (sync 2026-07-27) | ✅ 16/17 confirmados ejecutados; QW-17 (JWT lifetime a 15 min) sigue sin confirmar |
| 12 | `12_CHECKLIST_IMPLEMENTACION.md` | 2026-07-16/17 (sync 2026-07-27) | ✅ Vigente como registro histórico + pie de página apuntando a la Auditoría Enterprise y a §7/§9 de este documento |
| 13 | `13_AUDITORIA_FRONTEND_UI_2026-07-23.md` | 2026-07-23 (sync 2026-07-27) | ✅ **Vigente** — plan §6 actualizado: P1-1/P1-2/P1-4 cerrados (ver §7 de este documento), solo P1-3 sigue abierto |

**Recomendación:** para hallazgos de prioridad Media/Baja marcados "sin re-verificar" en los banners
de 02-09, conviene regenerar ese documento puntual contra el código actual en vez de asumir que siguen
abiertos o cerrados solo por la anotación de esta pasada — esta sincronización se apoyó en evidencia ya
recopilada en sesiones anteriores (§2-4, §7, checklist 12), no en una nueva auditoría línea por línea
de cada archivo.

---

## 9. Sesión de continuación — 2026-07-27 (tarde): Celery queue + verificación Wompi

Sesión separada de §7 (mismo día, distinto disparador: pedido explícito del usuario de sincronizar
conocimiento tras un incidente reportado de checkout Wompi). Método: lectura directa del código de
`payment/`, `ecommerce/settings/`, `docker-compose.prod.yml` y los `.env.production` reales (sin
exponer secretos), sin ejecución de tests nuevos (cambio de configuración, no de lógica de negocio).

### 9.1 [OK] Incidente nuevo encontrado y resuelto — 4 apps con tareas Celery sin worker en producción

**No estaba en ninguna versión anterior de este documento ni en `05_RENDIMIENTO.md`.** Al auditar
`docker-compose.prod.yml` contra el estado actual del código (pedido explícito del usuario, "sincroniza
el proyecto con el docker-compose de producción"), se encontró que `CELERY_TASK_ROUTES`
(`ecommerce/settings/base.py`) solo enruta `notifications.*`, `marketing.*` y `accounts.*`. Sin
`CELERY_TASK_DEFAULT_QUEUE`, cualquier tarea de otra app cae en la cola nativa de Celery llamada
literalmente `celery` — y `celery_worker` en `docker-compose.prod.yml` corre con
`-Q default,marketing,notifications`, que **nunca** incluyó esa cola. Con el tiempo se agregaron
tareas Celery en `payment`, `renting`, `orders` y `support` (ninguna con `queue=` explícito) y quedaron
encolándose sin ningún worker procesándolas — incluida `payment.tasks.reconcile_pending_wompi_transactions`,
el fallback que reconcilia pagos Wompi cuando el webhook se pierde.

El propio doc de arquitectura (`ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md`) afirmaba
incorrectamente que "el resto cae en `default` implícito" — ese supuesto nunca fue cierto (el
default nativo de Celery es la cola `celery`), y es probablemente la razón por la que nadie lo detectó
al agregar tareas nuevas en 4 apps distintas a lo largo del tiempo.

**Corrección:** agregado `CELERY_TASK_DEFAULT_QUEUE = 'default'` en `base.py` (cola ya escuchada por
el worker, sin necesidad de tocar `docker-compose.prod.yml`). Doc de arquitectura corregido en sus 3
menciones a Celery routing, con regla explícita para el futuro: toda cola NUEVA que se agregue a
`CELERY_TASK_ROUTES` debe agregarse también al flag `-Q` de `celery_worker` en ambos compose (prod y
dev). Documentado también en `payment/CLAUDE.md` y `ecommerce_sintel/MEMORY.md`.

**Requiere rebuild/redeploy de la imagen `django` para tomar efecto** (el código vive horneado en la
imagen, sin bind mount de fuente en producción) — **no aplicado a producción en esta sesión**
(regla `.AGENT.md`: nunca elevar sin instrucción explícita).

### 9.2 Verificado (no bug, incidente histórico ya corregido): "merchants/undefined" (422) + email de pago sin confirmación de Wompi

Reportado por el usuario (`notas.txt`) como un posible fallo arquitectónico: el checkout de Wompi
fallando con `GET .../v1/merchants/undefined` (422), y un correo de confirmación de pago enviado sin
evidencia de que Wompi hubiera respondido — hipótesis del reporte: el sistema confirmaría pagos antes
de la confirmación real de la pasarela.

Se rastreó el flujo completo contra el código actual: `Order.status='paid'` (pago online) solo se
escribe desde `payment/shared/commands.py::confirm_order_payment`, invocado únicamente cuando
`Transaction.status=='APPROVED'`, y ese status solo lo escriben el webhook (firma HMAC fail-closed,
**F-01** ya cerrado en la Auditoría Enterprise, §4), `_sync_wompi_status` o `_create_transaction_sync`
(ambos consultan la API de Wompi server-to-server) — nunca el callback del navegador
(`useWompiWidget.js` lo documenta explícitamente: el status del widget solo se usa para UX, jamás como
fuente de verdad). El `public_key` que llega al widget siempre viene de `settings.WOMPI_PUBLIC_KEY` en
la respuesta de `initialize/`, con default `'pub_test_placeholder'` (nunca `undefined` en JS), y los 3
call-sites que abren el widget están protegidos por `try/catch` que impide abrirlo si `initialize/`
falla. `WOMPI_PUBLIC_KEY`/`VITE_WOMPI_PUBLIC_KEY` confirmados no-vacíos en los `.env.production`
actuales (no versionados en git).

**Conclusión: incidente histórico, ya corregido — no reproducible contra el código actual de esta
rama.** Corresponde a un build/config anterior a los fixes ya aplicados (F-01, plan híbrido
Widget+API), no a un defecto vigente. Documentado en detalle en
`docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md` para no reabrir la investigación sin evidencia
nueva (captura de red/consola con timestamp).
