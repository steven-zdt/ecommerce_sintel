# 01 — Validación de Sincronización Documental

> **Fase 2 de la Auditoría de Gobernanza Documental.** Compara `IMPLEMENTATION_SUMMARY.md` ↔ cada
> `ARQUITECTURA_COMPLETA_<APP>.md` ↔ código real ↔ `docs/specs/` ↔ `CLAUDE.md`/`ANTIGRAVITY.md` de
> cada app, usando lectura completa de los 20 documentos de Nivel 2 (vía 7 subagentes de
> exploración paralelos) + verificación puntual contra código donde el hallazgo lo ameritó.
>
> **Estado de esta pasada:** 7 de 7 grupos de apps completados y consolidados abajo (Identidad,
> Comercio Core, Technical Services + Quotes, Orders + Payment, Renting + Marketing,
> Ops/Support/Notifications/Dashboard/Settings, Frontend/AI Engine/docs-specs). Auditoría completa.
>
> Ningún hallazgo de este documento ha sido corregido en el código o en los documentos fuente — es
> un reporte de auditoría, la corrección es responsabilidad de una decisión humana posterior (ver
> [[08_ARCHITECTURE_GOVERNANCE_MANUAL]]).

---

## 1. Clasificación de severidad usada

| Severidad | Criterio |
|---|---|
| **CRÍTICA** | El documento describe una funcionalidad que está rota en producción, o una contradicción de seguridad/dinero real |
| **ALTA** | Contradicción activa entre 2+ documentos vigentes, o un documento describe un endpoint/método que no existe en el código |
| **MEDIA** | Documento desactualizado en una sección puntual, o gap de documentación real (código sin documentar) |
| **BAJA** | Inconsistencia cosmética (fechas, roadmap no revisado) sin riesgo de inducir un error real |

---

## 2. Hallazgos CRÍTICOS

| ID | App(s) | Hallazgo | Evidencia |
|---|---|---|---|
| DOC-CRIT-01 | marketing | **Bug de producción real, no solo de documentación**: `marketing/agent/brain.py` y `marketing/tasks.py` importan `CampaignCommands` desde `marketing.services.commands` — esa clase **no existe**, la real se llama `MarketingCommands`. Provoca `ImportError` en tiempo de ejecución de la tarea Celery `run_marketing_agent_task` (el agente de marketing IA nunca corre) y en `send_via_channel_task` (ningún envío de campaña por canal funciona). Sin cobertura de tests que lo hubiera detectado. `ARQUITECTURA_COMPLETA_MARKETING.md` describe el flujo completo del agente como si funcionara, con diagramas paso a paso que nunca pudieron ejecutarse tal como están escritos desde que se introdujo esta discrepancia. | Grupo "renting+marketing", confirmado por grep exhaustivo en todo el repo |
| DOC-CRIT-02 | marketing | `ARQUITECTURA_COMPLETA_MARKETING.md` describe 2 endpoints que **no existen en el código**: `POST /api/v1/marketing/campaigns/{uuid}/dispatch/` y `POST /api/v1/marketing/agent/run/`. `MarketingCampaignViewSet` no tiene ninguna `@action`; no hay router para `agent/run/`. La única forma real de disparar el agente es una tarea Celery manual, no una API REST documentada — documentación aspiracional presentada como estado real. | Grupo "renting+marketing" |
| DOC-CRIT-03 | marketing | La sección "Validaciones y Seguridad" de `ARQUITECTURA_COMPLETA_MARKETING.md` dice textualmente que los permisos de API "no se muestran en el código, se presume `IsAuthenticated`" — es decir, el documento admite no haber verificado el permiso real. El código real ya tenía permisos correctos (`IsAdminUser`/`AllowAny` según ViewSet) desde un fix fechado **2026-07-03**, anterior a la fecha de "última actualización" que el propio documento declara (**2026-05-14**) — contradicción de fechas: o la fecha de actualización es falsa, o el documento nunca incorporó cambios de después de esa fecha pese a la etiqueta. | Grupo "renting+marketing" |
| DOC-CRIT-04 | docs/.AGENT/GUIA_AI_ENGINE.md | **Guía operativa activamente peligrosa.** Documenta como alternativa válida ("Opción 2") ejecutar `docker exec ecommerce_sintel_ai python auditor.py` dentro del contenedor para reindexar. Los otros 2 documentos hermanos del mismo AI Engine (`FLIJO_COMPLETO_IA_ENGINE.md` §2/§17.3 y `GUIA_USO.md` §7) advierten explícitamente lo contrario: ese comando **no lanza excepción**, reporta cada app como "(not found)" (por `BASE_DIR` incorrecto dentro del contenedor) y **sobrescribe silenciosamente `PROJECT_MAP.json` de producción con un archivo vacío de 0.4 KB**. Un operador que siga literalmente `GUIA_AI_ENGINE.md` puede degradar el AI Engine de todo el proyecto sin ningún error visible. | Grupo "frontend+ai_engine+docs-specs" |
| DOC-CRIT-05 | dashboard | `ARQUITECTURA_COMPLETA_DASHBOARD.md` afirma explícitamente "34 ViewSets + 1 APIView" y "36 de 37 clases declaran `permission_classes`" — verificado contra código real: **57 ViewSets** registrados en `dashboard/api/urls.py` (más 2 que viven físicamente en `operations`). 22 ViewSets completos (incluye `AdminSecurityViewSet`, `AdminNotificationTemplateViewSet`/`AdminNotificationLogViewSet`, y ~15 ViewSets satélite de detalle de Equipment/Service Packages) no aparecen mencionados en ninguna tabla del documento. Cualquier registro global que use "34 ViewSets" como fuente subestima la superficie real de la API admin en más de 60%. La cifra de cobertura de `permission_classes` tampoco es verificable para las 22 clases no contempladas. | Grupo "ops/support/notif/dashboard" |

---

## 3. Hallazgos ALTA severidad

| ID | App(s) | Hallazgo |
|---|---|---|
| DOC-ALT-01 | `.AGENT.md` (raíz) | **Contradicción interna del documento de reglas globales más importante del proyecto**: §7.1 ("Dirección de Dependencias") sigue nombrando la app de pagos `wompi` en su diagrama ASCII, mientras el resto del mismo archivo (§7.4, tabla anti-patrones §13) y absolutamente todo `IMPLEMENTATION_SUMMARY.md` usan `payment` y afirman explícitamente "la app nunca se llamó `wompi`". |
| DOC-ALT-02 | cart | `cart/CLAUDE.md` afirma explícitamente que `ARQUITECTURA_COMPLETA_CART.md` **"no existe, referenciado pero nunca creado"** — falso, el archivo existe, tiene 1375 líneas y fue actualizado la misma fecha (2026-07-03) que las correcciones que `CLAUDE.md` cita. `CLAUDE.md` no se actualizó tras la creación del doc. |
| DOC-ALT-03 | cart | `cart/ANTIGRAVITY.md` describe una arquitectura de datos distinta a la real en múltiples puntos: `GenericForeignKey` inexistente (real: 2 FK nullable + constraints), `Cart` como `OneToOne` (real: FK `unique=True`), métodos inventados (`get_or_create_cart()`, `get_cart_with_items()`, `delete_all()`) y una llamada a `InventorySelector.is_available()` que no existe. |
| DOC-ALT-04 | inventory | `inventory/ANTIGRAVITY.md` y el propio `ARQUITECTURA_COMPLETA_INVENTORY.md` (fecha 2026-05-14) documentan `register_entry()`/`register_exit()` con argumentos posicionales; `inventory/CLAUDE.md` (2026-07-03) confirma que esa firma **nunca existió**, el método real recibe un `StockAdjustmentDTO`. El doc "completo" oficial es el que está desactualizado, no una nota lateral. |
| DOC-ALT-05 | inventory | `InventorySelector.is_available()` y `get_stock_record_for_variant()` referenciados en `ANTIGRAVITY.md` **no existen** (confirmado por `CLAUDE.md`); tampoco están documentados los métodos reales (`get_current_stock()`, `get_stock_for_variant()` con caché 5 min) en el doc de arquitectura oficial. |
| DOC-ALT-06 | shop | `shop/ANTIGRAVITY.md` contradice la regla **[CRÍTICO]** vigente (confirmada en 2 documentos distintos) de que `delete_product()` debe setear `is_active=False` **Y** `is_deleted=True` — `ANTIGRAVITY.md` dice que solo usa `is_active=False`. |
| DOC-ALT-07 | accounts / users | `ARQUITECTURA_COMPLETA_ACCOUNTS.md` declara `VendorProfile` **eliminado** (2026-07-05, con migración). `ARQUITECTURA_COMPLETA_USER.md` sigue listando `user.vendor_profile` como acceso válido en su tabla de perfiles y `VendorProfileInline` como inline activo en `users/admin.py` — contradicción directa entre 2 documentos de Nivel 2. |
| DOC-ALT-08 | organization | Contradicción **dentro del mismo documento**: la tabla "Plan de migración (9 fases)" marca la Fase 8 (panel administrativo) como "Pendiente", pero el changelog inmediatamente debajo (misma fecha, 2026-07-12) describe ese panel ya construido y con tests pasando. |
| DOC-ALT-09 | organization | `organization/CLAUDE.md` dice "[EN CONSTRUCCIÓN — Fase 3 de 9]"; `ARQUITECTURA_COMPLETA_ORGANIZATION.md` (misma fecha) documenta Fases 1-8 completas o parciales. Un agente que solo lea `CLAUDE.md` concluiría erróneamente que la app es un skeleton. (Ya conocido y listado como pendiente en `IMPLEMENTATION_SUMMARY.md`.) |
| DOC-ALT-10 | payment | Contradicción **dentro de `ARQUITECTURA_COMPLETA_PAYMENT.md`**: la sección 2.5 (y su nota de "bug corregido 2026-07-03") afirma que TODOS los métodos de pago crean la orden en el mismo estado `STATUS_PENDING_PAYMENT`; los diagramas de flujo end-to-end de §6.2 (COD) y §6.3 (Nequi), a ~300 líneas de distancia en el mismo archivo, siguen usando los strings legacy `'processing'`/`'pending'` que ese mismo fix eliminó — exactamente el patrón de bug (comparar contra string legacy) que el documento dice haber corregido 3 veces. |
| DOC-ALT-11 | orders | `orders/CLAUDE.md` describe un modelo de estados obsoleto de 5 valores (`pending→paid→shipped→delivered→cancelled`) cuando el real tiene 16 estados y no existe `shipped`; atribuye la confirmación de pago a `PaymentCommands.confirm_payment()` cuando la ruta real y documentada es `payment.shared.commands.confirm_order_payment()`; y escribe mal la URL de checkout (`orders/create-from-cart/` en vez de `orders/orders/create_from_cart/`). No menciona en absoluto el motor de fulfillment. |
| DOC-ALT-12 | orders | El propio `ARQUITECTURA_COMPLETA_ORDERS.md` (doc "completo") **omite las 20 acciones staff-only del `OrderViewSet`** relacionadas al motor de fulfillment/Shop Operations (`prepare`, `pack`, `assign-*`, `dispatch`, `timeline`, `tracking`, etc.) de su propia tabla "Mapa completo de Endpoints" — un lector que confíe solo en esa tabla concluiría que `orders` es un CRUD simple sin saber que también es dueño de un subsistema logístico completo. |
| DOC-ALT-13 | kyc | El documento se auto-declara **"SUPERSEDED PARCIALMENTE (2026-07-06)"** al inicio: describe el diseño original (todo registro bloqueado hasta aprobación admin), ya no vigente, y redirige a `CLAUDE.md` — riesgo de que una lectura parcial (sin notar el banner) de las secciones no corregidas tome como verdad el diseño viejo. |
| DOC-ALT-14 | support | Confirmado (era sospecha, ahora hecho verificado): `ARQUITECTURA_COMPLETA_SUPPORT.md` afirma dos veces, sin matices, que "no existe `/api/v1/support/...`" y que el WebSocket es la única interfaz. Falta el endpoint `POST /api/v1/support/chats/<uuid>/rate/`, los 3 campos CSAT del modelo `ChatRoom` (`csat_rating`, `csat_comment`, `csat_rated_at`) y el método `ChatCommands.rate_conversation()`. Nota positiva: el gap de "modo AI" que `IMPLEMENTATION_SUMMARY.md` daba por pendiente ya estaba cerrado en una revisión del propio doc (2026-07-20, anterior a la nota de `IMPLEMENTATION_SUMMARY.md` del 2026-07-23) — ese documento quedó desactualizado en ese punto específico. |
| DOC-ALT-15 | frontend | `frontend/CLAUDE.md` (el archivo que un agente debería leer primero) contradice directamente a `ARQUITECTURA_COMPLETAFRONEND.md` (su propia fuente "LEER PRIMERO"): dice "1 único Pinia store, `auth.js`" cuando la arquitectura completa documenta **18 stores** y marca esa afirmación como "completamente falsa hoy"; dice "Sidebar con 5 grupos colapsables" cuando son **10 grupos** documentados explícitamente como corrección de esa misma cifra vieja. |
| DOC-ALT-16 | ai_engine | `docs/.AGENT/GUIA_AI_ENGINE.md` tiene métricas de artefactos completamente desactualizadas frente a `FLIJO_COMPLETO_IA_ENGINE.md`/`GUIA_USO.md` (ambos a 2026-07-19): "18 apps, 103 modelos, 76 ViewSets, 68 endpoints" vs. la cifra real verificada en runtime "21 apps, 166 modelos, 131 ViewSets, 118 endpoints, 385 archivos frontend". También su lista de "Apps disponibles" **omite `kyc`, `security`, `organization`** por completo. Ver también DOC-CRIT-04 (mismo archivo, hallazgo más grave). |
| DOC-ALT-17 | docs/specs/dashboard_bff.md | Afirma que existe un dominio BFF "Usuarios → `/api/v1/dashboard/users/`" y "Inventario → `/api/v1/dashboard/inventory/`". Ninguna de las dos rutas existe — `dashboard/api/urls.py` tiene el comentario explícito `# Users: administrado en /api/v1/users/, no aca`, y el ajuste de stock real vive en `/api/v1/inventory/stock-records/{uuid}/adjust_stock/`. El spec tampoco menciona los dominios reales de Quotes, Marketing, Core, Support, Security ni Operations/Dispatchers del BFF. |
| DOC-ALT-18 | docs/specs/frontend_vue.md | Documenta "5 stores existentes únicamente" (real: 18) y "40 rutas" (real: ~90); tabla de endpoints usa el prefijo `technical_services/` (real: `services/`) y rutas de escritura de Home inventadas (`dashboard/banners/`, `dashboard/modules/` — no existen); solo lista 6 composables de 20 reales; usa `import { useApi }` con llaves en sus ejemplos, contrato que `ARQUITECTURA_COMPLETAFRONEND.md` marca explícitamente como "rompe silenciosamente" (export es `default`). |
| DOC-ALT-19 | docs/specs/inventory.md | Documenta que `register_entry`/`register_exit` leen el balance vía `InventorySelector.get_current_stock()` (cache) dentro del bloque bloqueado — es exactamente el antipatrón que la regla crítica #11 del propio AI Engine bloquea; el código real usa `stock_record.stock` directo sobre el objeto ya bloqueado. También documenta `StockRecord.variant` como `OneToOneField` cuando el real es `GenericForeignKey` (content_type + object_id UUID). |
| DOC-ALT-20 | docs/specs/architecture_contracts.md, orders.md, renting.md, wompi.md | Las 4 comparten el mismo defecto raíz: nombran la app de pagos `wompi` (`architecture_contracts.md` en su "Estructura de Apps" y ejemplo de endpoint; `orders.md`/`renting.md` en `cross_app_dependencies`; `wompi.md` es el archivo completo, título incluido). `architecture_contracts.md` además omite `kyc`, `security`, `operations`, `organization` de su listado de apps — 4 de 20 apps de negocio ausentes de un documento que se presenta como el contrato de arquitectura del proyecto. |

---

## 4. Hallazgos MEDIA severidad

| ID | App(s) | Hallazgo |
|---|---|---|
| DOC-MED-01 | dashboard | `dashboard/.AGENT.md` existe pero está **completamente vacío (0 líneas)** — un archivo fantasma que puede confundirse con el doc de arquitectura real (`ARQUITECTURA_COMPLETA_DASHBOARD.md`). |
| DOC-MED-02 | shop | `ARQUITECTURA_COMPLETA_SHOP.md` §7.2 atribuye a **Orders** la validación de stock vía `InventorySelector.get_current_stock()`; §12 del mismo documento lista esa misma dependencia como un import propio de **shop** — contradicción interna sobre quién es responsable de qué. |
| DOC-MED-03 | shop / core | `core.HomeFeedSelector.get_featured_products()` delega en `ProductSelector.list_featured()`, método que **no aparece** en la tabla de métodos de `ProductSelector` documentada en `ARQUITECTURA_COMPLETA_SHOP.md` (posible drift entre 2 docs de Nivel 2, no confirmable sin leer código fuente). |
| DOC-MED-04 | inventory | Roadmap ("Mejoras Futuras") de `ARQUITECTURA_COMPLETA_INVENTORY.md` lista como pendiente un caché de saldo que `CLAUDE.md` ya documenta como implementado — el roadmap no se revisó desde mayo. |
| DOC-MED-05 | renting | `renting/api/internal_ai.py` (6 endpoints AI Core, incluye escritura con `SecurityEvent`) **no aparece mencionado en ninguna sección** de `ARQUITECTURA_COMPLETA_RENTIG.md`, pese a que ese documento se declara "auditado completo" el 2026-07-23 y el archivo vive en el mismo directorio que `views.py` (no es un rincón oculto del código). |
| DOC-MED-06 | marketing | `marketing/api/internal_ai.py` (5 endpoints AI Core) tampoco aparece mencionado en absoluto en `ARQUITECTURA_COMPLETA_MARKETING.md`. |
| DOC-MED-07 | marketing | `marketing/services/selectors.py::get_stale_stock_alerts()` accede a claves de dict (`['stale_equipment_count']`) sin `.get()` — si `RentingSummaryProvider` cambia su contrato de claves, produce un `KeyError` no capturado; riesgo de contrato implícito no reforzado. |
| DOC-MED-08 | marketing | `MarketingSelector` importa modelos `Order`/`OrderItem` directamente en 3 métodos, rompiendo el propio principio "Pull-based, nunca importar modelos de otras apps" que el mismo documento proclama como regla obligatoria — excepción real no reconocida como tal en la documentación. |
| DOC-MED-09 | payment | La tarea periódica `notify_declined_payments` (migración `0011`) solo aparece en la tabla de migraciones del doc SSoT, sin ninguna sección que documente su lógica — a diferencia de `reconcile_pending_wompi_transactions`, que sí tiene sub-sección propia. |
| DOC-MED-10 | payment→orders | La llamada `FulfillmentCommands.ensure_shipment_for_order()` desde `confirm_order_payment()` (paso 7) no estaba documentada en ningún lado hasta el ADR-001 Fase 0 (2026-07-13) — patrón repetido en el proyecto de dependencias cross-app que existen en el código pero se pierden de la documentación hasta una auditoría puntual. |
| DOC-MED-11 | quotes | Footer de `ARQUITECTURA_COMPLETA_QUOTES.md` declara "Última actualización: 2026-07-02", pero el cuerpo del documento referencia un fix fechado 2026-07-22 (HG-01) — el campo de fecha no es confiable como señal de vigencia real. |
| DOC-MED-12 | quotes | El mecanismo real detrás de "dispara email async" en `quotations/<uuid>/send/` no está documentado (¿Celery? ¿`on_commit`? ¿qué app lo ejecuta?) — hueco de documentación cross-app (afecta también al futuro registro de `notifications`). |
| DOC-MED-13 | technical_services | Los 6 archivos históricos de `technical_services/.AGENT/` (fuera de `docs/`) no tienen ningún marcador de "archivado/histórico" a nivel de nombre/carpeta — conviven al mismo nivel que archivos activos, riesgo de que un agente futuro los lea como vigentes. |
| DOC-MED-14 | users | `EmailVerificationCode` se usa extensamente (citado por `accounts`, `kyc`, y el propio `users/CLAUDE.md`) pero **nunca se documenta** en `ARQUITECTURA_COMPLETA_USER.md` — hueco real, no solo desactualización. |
| DOC-MED-15 | security | La superficie de "seguridad" real construida es mucho menor que el nombre de la app sugiere: 10 de 18 fases del brief original siguen "Pendiente" (middlewares, firewall, rate-limit, WebSocket protection, `SecurityCryptoService`, CSP/HSTS) — documentado honestamente por el propio doc, pero vale la pena que quede visible en el registro de gobernanza para expectativas correctas. |
| DOC-MED-16 | renting | Varios slugs de notificación (`rental_request_created`, `rental_payment_conflict_customer/admin`, `rental_request_rejected`, `rental_payment_failed`) seguían sin plantilla sembrada en BD según la última verificación (2026-07-07) — **no reconfirmado desde entonces**, riesgo de eventos "mudos" (el código dispara la notificación pero nunca sale). |
| DOC-MED-17 | orders/COD | `CodCommands.confirm_order()` no documenta explícitamente una guarda de idempotencia equivalente al `if order.status == STATUS_PAID: return` de `confirm_order_payment()` — riesgo potencial de doble-submit no cubierto por los docs (no confirmado contra código en esta pasada, solo señalado como hueco). |
| DOC-MED-18 | notifications | El doc (2026-07-09) declara canal SMS "explícitamente fuera de esta entrega". Cambios **sin commitear** en el working tree (fechados 2026-07-23) ya implementan `CHANNEL_SMS` completo (modelo, migración, cliente, tarea Celery, `sms_bridge/` como proceso externo nuevo) — contradicción real pero de una feature en curso, no aún en `main`. Marcar como "en progreso, no reflejar como vigente" hasta que se commitee. |
| DOC-MED-19 | notifications | "AI Core Event Bus" (Fase 7) — el Action Graph se suscribe como consumidor de `dispatch_notification()` vía comentario nuevo en el código (`# AI Core Event Bus`), sin ninguna sección en el doc de arquitectura que lo documente. |
| DOC-MED-20 | dashboard | Comandos nuevos `EquipmentCommercialConfigCommands`/`EquipmentCommercialOptionCommands` (feature "Comodato", 2026-07-22) importados directo en `admin_orchestrators.py` sin pasar por `RentingAdminOrchestrator` de forma documentada — no aparecen en `ARQUITECTURA_COMPLETA_DASHBOARD.md`. |
| DOC-MED-21 | operations | Cabecera declara "Última actualización: 2026-06-27" pero el cuerpo tiene anotaciones fechadas 2026-07-12 — la fecha de cabecera no es confiable como señal de vigencia (mismo patrón ya visto en `quotes`). No nombra las clases reales de las vistas de `/api/v1/operations/my/` y `/tasks/`, ni los permisos por nombre (`IsDispatcherUser`, etc.) que sí documenta `IMPLEMENTATION_SUMMARY.md`. |
| DOC-MED-22 | support | `ChatCommands` **no** llama a `NotificationCommands.dispatch_notification()` — mensajes nuevos de soporte no generan notificación push/email fuera del propio WebSocket. Es una limitación real de producto, reconocida explícitamente por el propio doc de `support` (no es un error de documentación). |
| DOC-MED-23 | ecommerce (core) | `asgi.py` importa `support.channels_auth.JWTAuthMiddlewareStack` como middleware WS **general** de todo el proyecto — el auth JWT de todo el WebSocket del sistema vive físicamente en la app `support`, acoplamiento no obvio y no documentado explícitamente en `ARQUITECTURACOMPLETA_SETTING.md`. |
| DOC-MED-24 | docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md | Fechado 2026-06-27, sin revisión posterior. Dos ítems que marca como pendientes ("Fase 1": validación temporal de cupones, y lectura de stock vía selector en vez de campo bloqueado) **ya están resueltos** en el código actual — riesgo de que alguien re-priorice trabajo ya hecho. |
| DOC-MED-25 | docs/specs/ (varios) | `cart.md` documenta `IsAuthenticatedActiveUser` para `WishlistViewSet` (real: `IsBuyerOrAdmin`, igual que `CartViewSet`); `technical_services.md` no menciona `IsServiceProviderUser`; `users_accounts.md` documenta `IsTechnicianUser` como mecanismo vigente cuando no se usa en ningún ViewSet del proyecto (el patrón real es `IsServiceProviderUser` sobre `SERVICE_PROVIDER_TYPES`), y su `USER_TYPE_CHOICES` omite `TRANSPORTER`/`ACCOUNTANT`. |
| DOC-MED-26 | docs/specs/payment.md | Hallazgo inverso, interesante: este spec (el más alineado de los 13) documenta `confirm_order_payment(order, reference)` con 2 argumentos — coincide con el código real. `.AGENT.md` raíz (§7.4/§8.3) documenta la misma función con **1 solo argumento** (`confirm_order_payment(order)`). En este caso puntual, el documento de Nivel 0 (`.AGENT.md`) es el que está desactualizado frente al spec de Nivel "paralelo". |

---

## 5. Hallazgos BAJA severidad / informativos

| ID | App(s) | Hallazgo |
|---|---|---|
| DOC-BAJ-01 | shop | Tres patrones de borrado distintos conviven en la misma app (`Product`/`Variant`: doble flag; `Category`: solo `is_active`; `Brand`: DELETE físico) — documentado, sin justificación de diseño explícita. |
| DOC-BAJ-02 | core | Única app del grupo "Comercio Core" sin `CLAUDE.md`/`ANTIGRAVITY.md` propio — asimetría de gobernanza, no necesariamente un error. |
| DOC-BAJ-03 | inventory / cart | Asimetría de concurrencia: `cart` usa `select_for_update()` en toda escritura crítica; `inventory` no lo usa en `register_entry`/`register_exit` pese a compartir el mismo dominio de datos (stock) — auto-reportado como riesgo en el propio doc de inventory, con fix propuesto no aplicado. |
| DOC-BAJ-04 | kyc | Estado `EXPIRED` del modelo documentado consistentemente en 2 lugares como "reservado, nada lo dispara" — deuda técnica visible, no contradicción. |
| DOC-BAJ-05 | accounts | Sección final declara explícitamente una "Fase 2 (pendiente, no ejecutada)" de separación de `UserProfile` por tipo — no priorizada a propósito. |
| DOC-BAJ-06 | technical_services | Documento más grande y más disciplinado del proyecto (2227 líneas, 4 pasadas de auditoría con rastro textual) — aun así admite no poder determinar cuándo una afirmación puntual (retiro de `TechnicianAssignmentBoard.vue` del sidebar) dejó de ser cierta, por falta de historial git granular. Riesgo estructural a vigilar en todo el proyecto: una afirmación de "estado actual" puede quedar obsoleta sin disparar actualización en cascada. |
| DOC-BAJ-07 | technical_services | `PLAN_UNIFICACION_SERVICES_CON_RENTING.md` — confirmado como plan **ya ejecutado en su totalidad** (las 6 fases), correctamente resumido en el doc principal. Único riesgo residual: el cuerpo del plan sigue redactado en tiempo futuro/imperativo sin anotación inline de que ya se ejecutó (el encabezado sí lo aclara). Quedan 2 ítems de backlog genuinos y correctamente marcados como abiertos (`video_url`, auditoría de badges compartidos). |
| DOC-BAJ-08 | payment | Los 12 documentos históricos (`ADR-001`, `AUDITORIA_*`, `FASE2..FASE9`) son bitácora cerrada, sin ninguna afirmación viva que el documento principal no refleje — evaluación explícita solicitada, resultado: ningún riesgo encontrado. El propio doc principal establece la jerarquía correcta en su encabezado ("el ADR es la fuente del diseño, este doc es la fuente del estado actual; ante diferencia, confiar en el código"). |
| DOC-BAJ-09 | shop / inventory / cart | Documentación despareja dentro del mismo grupo: `core` lleva bitácora fechada rigurosa; `cart` razonable; `inventory` sin auditoría desde 2026-05-14 pese a cambios reales de julio documentados solo en su `CLAUDE.md`; `shop` sin entradas de auditoría desde 2026-06-11. |

---

## 6. `docs/specs/` — veredicto final (13 de 13 archivos evaluados)

De los 13 archivos, **2 están razonablemente alineados** (`payment.md`, `notifications.md` — de
hecho `payment.md` acierta un detalle de firma de función que el propio `.AGENT.md` tiene mal, ver
DOC-MED-26), **2 casi sin contradicciones** (`shop.md`, `users_accounts.md` con matices menores), y
**9 de 13 tienen al menos una contradicción de severidad Alta** (ver DOC-ALT-17 a DOC-ALT-20,
DOC-MED-25). `docs/specs/wompi.md` es el único caso de **archivo completo obsoleto** — su contenido
técnico interno sigue siendo sustancialmente correcto, pero el nombre de app, prefijo de URL y
título completo del documento describen una app que no existe; es candidato directo a
fusionarse/reemplazarse por `payment.md`, que ya cubre el mismo dominio con el nombre correcto.

El patrón dominante de obsolescencia no es solo `wompi`→`payment` — también aparecen rutas BFF
inventadas (`dashboard_bff.md`, `frontend_vue.md`), y conteos de stores/composables/rutas del
frontend congelados en una versión muy temprana (`frontend_vue.md`: 5 stores documentados vs. 18
reales, 40 rutas vs. ~90 reales) — exactamente el mismo tipo de drift que
`ARQUITECTURA_COMPLETAFRONEND.md` ya identificó y corrigió para sí mismo el 2026-07-18. Ver regla
G7 en [[08_ARCHITECTURE_GOVERNANCE_MANUAL]] para la recomendación de gobernanza.

---

## 7. Cierre de la Fase 2

Auditoría completa: 20 documentos de Nivel 2 + `.AGENT.md`/`CLAUDE.md` raíz + `IMPLEMENTATION_SUMMARY.md`
+ 13 archivos de `docs/specs/` + documentos cross-app de `docs/.AGENT/` + `ai_engine/.AGENT/` +
`frontend/.AGENT/`. Total: **5 hallazgos CRÍTICOS, 20 ALTA, 26 MEDIA, 9 BAJA/informativos**.

Ver consolidación de todos estos hallazgos en formato "registro" en
[[06_CROSS_MODULE_REGISTRY]] (riesgos cross-app) y [[07_KNOWLEDGE_REGISTRY]] (duplicación de
conocimiento).
