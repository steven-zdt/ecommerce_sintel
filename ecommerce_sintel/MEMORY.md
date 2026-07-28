# MEMORY.md - Memoria del Proyecto Sintel E-Commerce

**Estado Actual:** `EN DESARROLLO - DEVELOPMENT`

Este documento sirve como registro activo de la memoria del proyecto para asegurar la continuidad del contexto entre sesiones de desarrollo, alineado con las reglas globales establecidas en `.AGENT.md`.

**Paso 2 del flujo de consulta jerarquico** (ver `.AGENT.md` -> "FLUJO OBLIGATORIO ANTES DE MODIFICAR CODIGO"): leer este archivo justo despues de `.AGENT.md` y antes de entrar al doc de una app especifica. Para el estado detallado y actualizado app-por-app, ver `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` — el historial de abajo (Mayo-Junio 2026) no se ha actualizado con las fases posteriores (kyc, security, operations, dashboard, core, notifications, support, Cloudflare Tunnel, etc.), documentadas en ese archivo y no aqui.

## 1. Identidad y Contexto AI
- **Agente Asignado:** Antigravity (AI Agent)
- **Instrucciones Base:** Validadas a través de los archivos `ANTIGRAVITY.md` (antes CLAUDE.md) distribuidos en la raíz y en cada uno de los módulos de la aplicación.
- **Objetivo Principal:** Mantener estricta adherencia a la arquitectura modular de Sintel v3.5.

## 2. Alineación con Reglas Generales (.AGENT.md)
Toda interacción y modificación de código respeta obligatoriamente los siguientes patrones:
1. **Service Layer:** Prohibido lógica de negocio en ViewSets. Se usan `*Commands` para escrituras atómicas y `*Selectors` para lecturas optimizadas (evitando N+1).
2. **Modelo Base y UUIDs:** Todo modelo hereda de `SintelBaseModel`. Las URLs y APIs exponen y operan usando `uuid`, nunca `pk` o `id`.
3. **Inmutabilidad y Soft-Delete:** No se borran registros físicamente (`is_active=False` o `is_deleted=True`). Se aplican Snapshots (ej. en `OrderItem` o `QuotationItem`) para mantener historial inmutable.
4. **Roles y Permisos:** Uso estricto de las clases de permisos del módulo `users` (ej. `IsAdminUser` que valida rol y no solo `is_staff`).
5. **Composables en Frontend:** En Vue.js 3, las peticiones se realizan a través de `useApi()` y el estado con `useAuth()`, evitando llamar a `axios` directamente en los componentes.

## 3. Estado de la Infraestructura
- **Backend:** Django 5.2.13 + DRF + PostgreSQL + Redis + Celery + Channels (WebSockets).
- **Frontend:** Vue.js 3 + Vite + Pinia + Vue Router + Axios + Bootstrap 5.
- **Entorno:** Dockerizado (`docker compose up` activo).

## 4. Historial Reciente y Tareas Actuales (Julio 2026)

- **Bug real cerrado: tareas Celery de 4 apps sin worker escuchandolas en produccion
  (2026-07-27, encontrado auditando `docker-compose.prod.yml` contra el estado actual del
  codigo, a peticion del usuario tras cerrar los 9 hallazgos P0 de `a457ac6`):**
  `CELERY_TASK_ROUTES` (`ecommerce/settings/base.py`) solo enruta `notifications.*`,
  `marketing.*` y `accounts.*`; sin `CELERY_TASK_DEFAULT_QUEUE`, cualquier tarea de otra app
  cae en la cola nativa de Celery llamada `celery` -- y `celery_worker` en
  `docker-compose.prod.yml` corre con `-Q default,marketing,notifications`, que NUNCA
  incluyo esa cola. Con el tiempo se agregaron tareas Celery en `payment`, `renting`,
  `orders` y `support` (ninguna con `queue=` explicito) y quedaron encolandose sin ningun
  worker procesandolas -- incluida `payment.tasks.reconcile_pending_wompi_transactions`, el
  fallback que reconcilia pagos Wompi cuando el webhook se pierde. El propio doc de
  arquitectura (`ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md`) afirmaba
  incorrectamente que "el resto cae en default implicito" -- ese supuesto nunca fue cierto,
  y por eso nadie lo detecto al agregar tareas nuevas. **Fix:** agregado
  `CELERY_TASK_DEFAULT_QUEUE = 'default'` en `base.py` (cola ya escuchada por el worker, sin
  tocar `docker-compose.prod.yml`). Doc de arquitectura corregido en sus 3 menciones a
  Celery routing, con regla explicita para el futuro: toda cola NUEVA que se agregue a
  `CELERY_TASK_ROUTES` debe agregarse tambien al flag `-Q` de `celery_worker` en ambos
  compose (prod y dev), o sus tareas quedaran igual de huerfanas. **Requiere rebuild/redeploy
  de la imagen `django` para tomar efecto** (el codigo vive horneado en la imagen, no hay
  bind mount de fuente en produccion) -- no aplicado a produccion en esta sesion (regla
  `.AGENT.md`: nunca elevar sin instruccion explicita).

- **Verificacion (no bug, incidente historico ya corregido): "merchants/undefined" (422) +
  email de pago sin confirmacion de Wompi (2026-07-27, reportado por el usuario via
  `notas.txt`):** se rastreo el flujo completo -- `Order.status='paid'` (pago online) solo
  se escribe desde `payment/shared/commands.py::confirm_order_payment`, invocado unicamente
  cuando `Transaction.status=='APPROVED'`, y ese status solo lo escriben el webhook (firma
  HMAC fail-closed, F-01 ya cerrado), `_sync_wompi_status` o `_create_transaction_sync`
  (ambos consultan la API de Wompi server-to-server) -- nunca el callback del navegador
  (`useWompiWidget.js` lo documenta explicitamente). El `public_key` que llega al widget
  siempre viene de `settings.WOMPI_PUBLIC_KEY` en la respuesta de `initialize/`, con default
  `'pub_test_placeholder'` (nunca `undefined` en JS), y los 3 call-sites que abren el widget
  estan protegidos por `try/catch` que impide abrirlo si `initialize/` falla.
  `WOMPI_PUBLIC_KEY`/`VITE_WOMPI_PUBLIC_KEY` confirmados no-vacios en los `.env.production`
  actuales (no versionados en git). Conclusion: el incidente reportado corresponde a un
  build/config anterior a los fixes ya aplicados, no a un defecto vigente -- documentado en
  `docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md` para no reabrir la investigacion
  sin evidencia nueva (captura de red/consola con timestamp).

- **Fase 11 AI Core -- cierre (2026-07-21):** de los 2 escenarios que quedaron fuera del
  alcance original de Fase 11, la investigacion confirmo que **"renovacion de contratos" se
  solapa 100% con "renting por vencer"** (ya construida) -- `RentalRequest`/`RentalPeriod` es
  el UNICO concepto de "contrato" en todo el proyecto, no hay servicios tecnicos recurrentes
  ni suscripciones en ningun dominio. Se cierra formalmente sin duplicar. Para "clientes
  recurrentes/venta cruzada" se implemento un cross-sell MINIMO (decision explicita del
  usuario: sin motor de recomendacion, que no existe en el proyecto -- `marketing.PersonalOffer`
  existe como vehiculo pero exige elegir variante/producto especifico, y cualquier eleccion
  seria arbitraria sin logica real de recomendacion): `orders/tasks.py` (nuevo, primera tarea
  Celery de esa app) `notify_frequent_customers_cross_sell` detecta clientes con 3+ `Order`
  pagadas (query de agregacion simple, sin modelo nuevo) y envia UN mensaje generico de
  reconocimiento por cliente (dedupe de por vida, no por Order) via el mismo Event Bus de
  Fase 11 (`NotificationCommands.dispatch_notification_once`, reusando la clave `message` ya
  reconocida -- no hizo falta tocar `notifications/tasks.py`). Nuevo slug
  `cliente_recurrente_cross_sell` (`notifications/migrations/0005_seed_cross_sell_template.py`)
  agregado a `AI_PROACTIVE_SLUGS`. Verificado con datos reales de dev: 2 clientes (5 y 6
  ordenes pagadas) recibieron el mensaje correctamente, dedupe confirmado (0->2->2), visible
  en `/panel/soporte`. **Con esto, Fase 11 queda 5/6 resuelta formalmente (4 tareas +
  cross-sell) y el 6to (renovacion de contratos) cerrado por redundancia, no por omision.**

- **CSAT -- Satisfaccion del Cliente en el Chat de Soporte (2026-07-21, retomado de los 2
  items descartados en Fase 9; el usuario eligio este):** `ChatRoom` gana 3 campos
  (`csat_rating` 1-5, `csat_comment`, `csat_rated_at`, migracion `support/0008_chatroom_csat.py`)
  y `ChatCommands.rate_conversation()` (mismo patron de validacion --ownership + estado
  terminal-- que `renting.EquipmentReviewCommands.create_review()`). **Hallazgo real durante
  la investigacion:** cerrar una sala era, hasta ahora, un UPDATE de BD silencioso -- el
  cliente conectado nunca se enteraba en tiempo real (`ChatCommands.close_room()` no hacia
  `group_send`). Se agrego el aviso (`'type': 'room.closed'` -> `SupportChatConsumer.room_closed()`,
  mismo patron que `ai_proactive_room_message_task`), sin el cual el widget nunca podria
  ofrecer calificar. Primera REST API publica de `support` (antes 100% WebSocket):
  `POST /api/v1/support/chats/{uuid}/rate/` (`support/api/views.py`+`urls.py`, nuevos,
  registrados en `ecommerce/urls.py`). Frontend: `SupportChatWidget.vue` (el widget del
  CLIENTE, no `SupportDashboardView.vue` que es el panel admin) ahora escucha
  `'room_closed'` y muestra un prompt de 5 estrellas + comentario opcional;
  `SupportDashboardView.vue` muestra el rating como badge de estrellas en el header de la
  sala. `ChatAnalyticsSelector.get_summary()` (Fase 9) suma `avg_csat`/`csat_responses_count`
  (campo numerico real -- a diferencia de `ai_metrics`, aca `Avg()`/`Count()` de Django ORM
  son seguros directamente). Verificado end-to-end con un flujo real de 2 sesiones de
  navegador (cliente + admin): cerrar la sala via API real -> el widget del cliente recibe
  el evento WS y muestra el prompt EN VIVO -> se califica con 5 estrellas + comentario ->
  se confirma persistido en BD y expuesto por `ChatRoomSerializer`. **Gap real encontrado
  durante la verificacion (delegado como tarea aparte, no corregido aqui):** el Dashboard de
  Soporte solo lista salas `status=OPEN` (`ChatSelector.get_active_rooms()`) -- en cuanto se
  cierra una sala desaparece de la lista, asi que hoy un admin no tiene forma de navegar en
  la UI a una conversacion cerrada para ver el CSAT que dejo el cliente (el badge SI
  funciona, solo que no hay como llegar a el por falta de un filtro "Cerradas"). **Nota
  operativa:** para la verificacion visual se reutilizo `admin3@sintel.com` (fixture de
  prueba de sesiones anteriores) como cliente de prueba -- se le seteo una password temporal
  conocida (`DevFixtureTemp123!`) para poder loguearse como cliente real en el navegador; es
  dev-only, no una cuenta real.

- **Fase 9 AI Core -- Analytics de Conversaciones del Copilot de Soporte (2026-07-20, ULTIMA
  fase pendiente del plan "Support AI Platform" tras Fase 8, 11 y 12):** alcance acordado con
  el usuario: solo el dashboard de analytics (FAQs + problemas frecuentes) sobre datos que YA
  existen -- sin modelo de satisfaccion (CSAT) ni persistencia de productos consultados por
  Tool (ambos descartados explicitamente, mas alcance/incertidumbre del que pedia esta fase).
  "Reentrenar prompts"/"mejorar respuestas" (parte del pedido original) no son features de
  codigo -- son ediciones manuales a `ai_engine/agents/profiles/*.yaml` informadas por estos
  numeros, no algo para automatizar. Nuevo: `support/services/selectors.py::ChatAnalyticsSelector.get_summary(days=30)`
  -- una query a `ChatMessage.ai_metrics` (JSONField, Fase 8) en la ventana + TODO el computo
  (promedios, tasas, `Counter` por intent/tool) en una sola pasada de Python (decision
  deliberada: se evito `Cast`/`KeyTransform` de Django ORM sobre JSON para agregaciones
  numericas/de arreglos, no probado en este proyecto y con riesgo real de resultado
  silenciosamente incorrecto). Expuesto via `dashboard/services/admin_orchestrators.py::
  SupportAdminOrchestrator.get_analytics_summary()` (se reutilizo el orchestrator de support
  YA existente en vez de crear uno nuevo en paralelo) + accion nueva
  `GET /api/v1/dashboard/support/chats/analytics/?days=30` en el `AdminSupportChatViewSet` ya
  registrado (no hizo falta tocar `urls.py`: al ser un `@action` de un ViewSet con router, la
  ruta se genera sola). Frontend: nueva seccion en `SupportDashboardView.vue` (tarjetas KPI +
  2 tablas "Preguntas mas frecuentes"/"Problemas frecuentes"), reusando clases CSS
  (`.kpi-card`, `.top-product-list`, etc.) ya definidas en `views/admin/DashboardView.vue`.
  Verificado con datos reales de las Fases 8/11 de esta sesion + test nuevo en
  `support/tests.py` (9no caso, sincrono, sin WebSocket) + confirmado visualmente en
  `/panel/soporte` con los mismos numeros que el shell. Con esto, el plan "Support AI
  Platform" (Fases 1-12) queda completo.

- **Fase 11 AI Core -- Proactividad del Copilot de Soporte (2026-07-20, continuacion del plan
  "Support AI Platform" tras Fase 8 y Fase 12):** hallazgo clave: la infraestructura ya existia
  (Event Bus "Componente 8", Fase 7) --
  `notifications/services/commands.py::NotificationCommands.dispatch_notification` ya
  revisaba `settings.AI_PROACTIVE_SLUGS` y disparaba
  `notifications/tasks.py::ai_proactive_room_message_task` (mensaje del bot en la sala de
  soporte del cliente via el mismo WS de siempre) -- pero `AI_PROACTIVE_SLUGS` solo tenia 1
  slug reactivo (`order_payment_confirmed`) y ningun scanner periodico disparaba los 6
  escenarios pedidos por el usuario. Implementados 4 de los 6 (los otros 2 -- clientes
  recurrentes/venta cruzada, renovacion de contratos -- quedan fuera, requieren logica de
  negocio/marketing nueva sin campo de modelo listo, decision explicita del usuario):
  - `quotes/tasks.py::notify_quotations_without_response` (nueva, diario 9am): `Quotation`
    en ENVIADA sin respuesta en 3 dias.
  - `renting/tasks.py::notify_rentals_expiring_soon` (nueva, diario 9am): `RentalPeriod`
    activo con `end_date` a 3 dias o menos.
  - `payment/tasks.py::notify_declined_payments_followup` (nueva, cada hora):
    `Transaction` DECLINED en las ultimas 24h.
  - `support/tasks.py::notify_unattended_escalated_tickets` (app nueva, primera tarea
    Celery de `support`, cada hora): `ChatRoom` escalada a humano (`ai_paused=True`) sin
    actividad en 2h.
  Cada una registrada como `PeriodicTask` via migracion data (mismo patron idempotente que
  `payment/migrations/0008_seed_reconcile_periodic_task.py`); 4 `NotificationTemplate` nuevas
  sembradas por migracion (`notifications/migrations/0004_seed_proactive_templates.py` --
  primera vez que se siembra `NotificationTemplate` por migracion, extension del mismo
  idioma usado para `PeriodicTask`); `AI_PROACTIVE_SLUGS` actualizado en `.env` (ahora
  `order_payment_confirmed,cotizacion_sin_respuesta,renting_por_vencer,pago_rechazado_seguimiento,ticket_soporte_sin_seguimiento`)
  y documentado en `.env.production.example`.
  **Bug real encontrado y corregido durante la verificacion:** el dedupe inicial (chequear
  `NotificationLog` antes de notificar) tenia una condicion de carrera -- esos logs los crean
  las tareas Celery async POR CANAL (`send_ws/email/whatsapp_notification_task`), no la
  llamada sincrona, asi que dos corridas rapidas del scanner podian notificar la misma
  entidad dos veces antes de que el log async aterrizara. Fix: nuevo metodo
  `NotificationCommands.dispatch_notification_once(user, template_slug, context, dedupe_key)`
  (`notifications/services/commands.py`) que crea su propio marcador `NotificationLog`
  (`channel=''`) de forma SINCRONA antes de llamar a `dispatch_notification` -- las 4 tareas
  lo usan en vez de checkear `NotificationLog` directamente. Otro hallazgo operativo: en este
  entorno, `docker compose restart` NO relee cambios de `.env` (hay que usar
  `docker compose up -d <servicio>` para recrear el contenedor) -- causo que la primera
  verificacion pareciera fallar silenciosamente (el Event Bus no se activaba) hasta
  diagnosticar que `settings.AI_PROACTIVE_SLUGS` seguia con el valor viejo. Verificado
  end-to-end para los 4 escenarios: tarea sincrona -> `NotificationLog` marcador creado ->
  segunda corrida no duplica -> `ChatMessage` del bot real en la sala -> confirmado
  visualmente en `/panel/soporte`.

- **Fase 12 AI Core -- Validacion funcional del Copilot de Soporte (2026-07-20, continuacion
  del plan "Support AI Platform" tras Fase 8):** primer test suite de `support`
  (`support/tests.py`, no existia ninguno antes), pytest-django + Django Channels
  (`WebsocketCommunicator`) + `pytest-asyncio` (`@pytest.mark.asyncio`, primer uso en el repo) --
  8 casos: inicio de conversacion, recuperacion de contexto (Order propia/ajena), respuesta de
  IA + persistencia de `ai_metrics`, flujo de confirmacion de escritura (2 turnos), Human
  Handoff (`ai_paused`), persistencia de historial tras reconexion, sincronizacion Dashboard
  admin <-> widget cliente (2 comunicadores concurrentes), y concurrencia (N=5 chats
  simultaneos sin cruces de sala). `ai_bridge.ask_ai` se mockea siempre
  (`@patch('support.services.ai_bridge.requests.post')`) -- **hallazgo importante:** el
  entorno real (`ecommerce.settings.production`, `.env`) tiene `AI_SUPPORT_CHAT_ENABLED=True`
  por defecto, asi que cualquier test que envie un mensaje de cliente sin mockear ai_bridge
  dispara una llamada real al AI Engine en segundo plano -- los tests que no prueban IA fuerzan
  `override_settings(AI_SUPPORT_CHAT_ENABLED=False)` explicitamente. El test de concurrencia es
  intermitente por `TimeoutError` en este host (~1 de cada 5 corridas, I/O real de Postgres bajo
  carga concurrente medido con `TRUNCATE`, nunca por un cruce real de sala) -- documentado en el
  propio test, no es un bug de la app. Tambien nuevo: `ai_engine/e2e_http/e2e_support_ai_chat_test.ps1`
  (mismo patron que los otros scripts de ese directorio) -- valida disponibilidad, latencia real
  (~2-3s por turno simple, sube a ~7-33s bajo 5 llamadas paralelas por contencion de Ollama
  local) y concurrencia real contra el stack vivo, solo con Tools de lectura (sin escritura real
  para no ensuciar la BD de desarrollo). Hallazgos fuera de alcance detectados de pasada
  (delegados como tareas separadas, no corregidos aqui): (1)
  `core/tests/test_models_and_signals.py::TestCacheInvalidationOnDelete::test_footer_link_deletion_invalidates_cache`
  falla de forma pre-existente y reproducible (`IntegrityError` por `group_id` NULL en
  `FooterLink`), sin relacion con `support`/`ai_engine`; (2) el Dockerfile de este proyecto
  exporta solo el grupo `main` de Poetry (`poetry export --without-hashes` sin `--with dev`),
  por lo que el contenedor `django` no tiene `pytest`/`pytest-django`/`pytest-asyncio` pese a que
  `COMANDOS.txt` documenta `docker compose exec django pytest` como el comando oficial -- hubo
  que instalar esas dependencias de forma efimera (`pip install --user`, `HOME=/tmp`) para correr
  esta suite.

- **Documentado: integracion `support` <-> `ai_engine` (Copilot de Soporte) ya construida +
  Fase 8 Panel Admin nueva (2026-07-20, pedido explicito de validar contexto y ejecutar el
  plan "Support AI Platform"):** al validar el pedido del usuario (convertir el chat de
  Support en un Copilot respaldado por el AI Engine: WebSocket como canal, LangGraph/Action
  Graph como cerebro) se confirmo que las Fases 1-7 y 10 de ese plan **ya estaban
  implementadas y en produccion desde 2026-07-16** (`ai_engine/.AGENT/PLAN_DE_ACCION_AI_CORE.md`:
  9 Agent Profiles, 29 Tools/Capabilities, Context Builder, Human Handoff via
  `ChatRoom.ai_paused` + `support/api/internal_ai.py::AiOpenSupportTicketView`), pero sin
  ninguna entrada en este archivo ni en
  `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` (que todavia describe support como
  un chat sin IA) — gap de documentacion, no de codigo. De los gaps reales (Fase 8 Panel
  Admin, Fase 9 Aprendizaje, Fase 11 Proactividad, Fase 12 Validacion funcional), el usuario
  eligio Fase 8 primero. Implementado: `ai_engine/observability.py::TurnMetrics` (agente,
  intent, tools ejecutadas con tiempo, tokens LLM in/out, duracion, handoff,
  needs_confirmation, fallback_used) se calculaba por turno pero solo se emitia a un log JSON
  y se descartaba -- ahora `run_action_chat` (`ai_engine/action_graph.py`) lo incluye en el
  dict de retorno y `ChatResponse` (`ai_engine/main.py`) expone el campo opcional `metrics`;
  Django persiste eso en el mensaje del bot via `ChatMessage.ai_metrics` (JSONField nullable,
  migracion `support/0006_chatmessage_ai_metrics`), pasado desde
  `consumers.py::_save_ai_message_and_maybe_pause` a traves de
  `ChatCommands.save_message(..., ai_metrics=...)` (parametro opcional, compatible con los 4
  llamadores existentes); expuesto solo en `ChatMessageSerializer` (usado unicamente por
  `dashboard/api/views.py::AdminSupportChatViewSet`, `support` no tiene URLs REST propias) y
  renderizado como badges en `SupportDashboardView.vue`. Decision explicita: no se toco
  `SupportChatConsumer.chat_message()` (el broadcast WS), por lo que la telemetria **nunca
  viaja por el canal en vivo** (ni al cliente ni al admin) -- solo aparece al abrir/reabrir
  la sala por REST, para evitar cualquier riesgo de filtrar datos internos por WS. No existe
  un "confidence score" en el motor; no se inventa uno, se muestra solo lo que el grafo
  realmente calcula.

- **Fix: 415 al subir imagen de servicio (2026-07-18, reportado por el usuario):**
  `dashboard/services/{uuid}/add_image/` devolvia 415 Unsupported Media Type. Causa:
  `technicalServicesAdmin/services.js::uploadImage()` no pasaba
  `{ headers: { 'Content-Type': 'multipart/form-data' } }` al hacer POST con `FormData` —
  el default global de `useApi()` (`Content-Type: application/json`) gana sobre la
  deteccion automatica de `FormData`, y esa era la unica llamada de upload de todo el
  proyecto sin el override (~20 call-sites ya lo hacian bien). Un-line fix + verificado con
  Playwright real (subida real, 201, toast de exito). Documentado en
  `ai_skills/frontend/architecture/vue_patterns.md` para evitar que se repita en llamadas
  nuevas.

- **Plan de Unificacion Services<->Renting: COMPLETO, 6/6 fases (2026-07-18, pedido
  explicito "finaliza en su totalidad todas las fases pendientes"):** cierre de las Fases
  4-6 sobre lo ya hecho en Fases 1-3 (ver entrada anterior). Fase 4: `ServiceDetailView.vue`
  paso de monolito de 536 lineas sin subcomponentes a 8 componentes nuevos en
  `components/services/detail/` (Galeria/Recursos tecnicos/Alcance/Ficha tecnica/FAQ/
  Profesionales/Resenas); bloque "Profesionales" nuevo expone
  `TechnicianSelector.get_available_for_category` (ya existia) via
  `GET services/services/{uuid}/technicians/`; bloque "Antes y despues" eliminado
  (recomendacion explicita del plan, no existe equivalente conceptual en servicios
  tecnicos). Fase 5: sidebar de resumen persistente en el wizard
  (`ServiceRequestSummary.vue`, pasos 2-3, reutiliza `ServicePriceBreakdown` ya existente) +
  `CheckoutStepper.vue` generalizado (prop `clickable` nuevo) y ahora compartido entre
  `RentalBookingWizard.vue` **y** `ServiceRequestWizard.vue` (toco codigo de Renting
  tambien, verificado que la navegacion clickeable de Renting sigue igual). Fase 6:
  `OperationTimeline.vue` resulto YA estar migrado a `StatusTimeline.vue` desde antes de
  este plan -- se corrigio la documentacion en vez de hacer trabajo redundante; ademas se
  agregaron 3 campos SEO editables (meta_title/meta_description/meta_keywords) al tab
  General de `ServiceForm.vue`. Verificado con `manage.py test technical_services dashboard
  renting` (256 tests, 0 regresiones) + Playwright (detalle completo, sidebar del wizard,
  navegacion del stepper) + `npm run build` limpio en cada tanda. Documentacion actualizada:
  `ai_skills/frontend/components/cards.md` (§2 CheckoutStepper, §4.2 nuevo), 
  `technical_services/CLAUDE.md`, `ARQUITECTURA_COMPLETA_SERVICES.md` (§16 C9), y el propio
  plan (checklists tecnico/UX/UI marcados, estado de ejecucion final).

- **Fase 4 (arranque, superada por la entrada de arriba) del Plan de Unificacion
  Services<->Renting (2026-07-18, pedido explicito "continua las fases faltantes"):** sin
  respuesta a la pregunta de color pendiente
  (Etapa 8), se procedio con la recomendacion por defecto ya documentada en el plan (mantener
  ambar `#d97706` en catalogo/detalle de servicios). Hecho: (1) `ServiceReview` (modelo real
  con datos, cero exposicion API previa) ahora expuesto — `ServiceReviewSelector`/
  `ServiceReviewCommands` nuevos en `technical_services/services/marketing.py` (mismo patron
  "ownership + estado terminal" que `renting.EquipmentReviewCommands`, adaptado a
  `ServiceOperation.CLOSED` como estado terminal, via el camino real `Order ->
  OrderServiceDetail -> ServiceBooking -> ServiceVariant -> TechnicalService`, ya que este
  dominio no tiene un modelo "request" unico como `RentalRequest`); nuevas acciones `GET/POST
  services/services/{uuid}/reviews//review/` en `TechnicalServiceViewSet` (mismo shape que
  `EquipmentViewSet.reviews`/`.review`); nuevo componente
  `frontend/src/components/services/detail/ServiceReviews.vue` (ambar), montado en
  `ServiceDetailView.vue` en una seccion "Opiniones" nueva. Verificado end-to-end con Django
  test Client (anon GET, POST sin historial de servicio->400, POST con `ServiceOperation`
  CLOSED real->201, duplicado->400, GET refleja el nuevo review) + `manage.py test
  technical_services` (108 tests, misma 1 falla preexistente no relacionada de fechas) +
  `npm run build` limpio. (2) Confirmado que la seccion FAQ del detalle publico YA estaba
  conectada a datos reales desde la Fase 2/3 (el computed `faqs` existente en
  `ServiceDetailView.vue` ya esperaba exactamente la forma `question`/`answer` que expone
  `ServiceFAQSerializer`) — cero cambios de frontend necesarios, solo se verifico creando una
  `ServiceFAQ` de prueba y confirmando el payload real del endpoint publico. Deliberadamente
  NO construido sin pedido explicito: los bloques Alcance/Recursos-tecnicos/propuesta-de-
  valor/`success_case` de `ServiceDetailView.vue` siguen 100% hardcodeados (`pickList()` cae
  siempre al fallback porque ningun nombre de campo que prueba existe hoy en
  `TechnicalService`/`ServiceMarketing`) — hacerlos data-driven exigiria ~9 modelos backend
  nuevos (espejo de `RentalIncludedItem`/`RentalFeature`/`RentalSpecificationGroup`/etc. de
  Renting), una expansion bastante mayor que "componentizar" tal como estaba alcanzado en el
  plan original. Video y Antes/Despues siguen sin dato real de origen. Fases 5-6 (sidebar
  persistente del wizard, `WizardStepper.vue` compartido, migrar `OperationTimeline.vue` a
  `StatusTimeline.vue`) siguen pendientes.

- **Fase 3 del Plan de Unificacion Services<->Renting EJECUTADA (2026-07-18, pedido
  explicito "continua"):** `ServiceForm.vue` (panel admin) gano 2 tabs nuevos conectados a
  los endpoints de la Fase 2 (2026-07-17): "FAQ" y "Marketing". El tab Marketing replica
  casi campo a campo el de `RentingForm.vue` (precio comercial, etiquetas, mensajes de
  conversion, casos de uso, CTA/banner, beneficios rapidos — sin la comparativa
  comprar-vs-alquilar, que no aplica). El tab FAQ usa un componente NUEVO Y DEDICADO,
  `ServiceFAQManager.vue` (`frontend/src/modules/technical_services/`), en vez de
  generalizar los 6 managers admin genericos de Renting (decision ya tomada en la Fase 1:
  esos 6 componentes no aceptan endpoint/nombre-de-campo-FK como prop, generalizarlos
  tocaria 6 archivos de produccion de Renting sin pedido explicito) — mismo patron de
  interaccion (drag-reorder, alta/edicion inline, toggle-active), llamando directo a
  `dashboard/service-faqs/`. Verificado end-to-end con Playwright real contra el panel
  admin (login, abrir "Servicio Fijo Prueba" en edicion, crear una FAQ, guardar Marketing) —
  ambas acciones con toast de exito, cero errores de red/consola. Build de produccion
  limpio. Documentado en `PLAN_UNIFICACION_SERVICES_CON_RENTING.md` (estado de ejecucion +
  Etapa 4.3), `technical_services/CLAUDE.md`, y `ai_skills/frontend/components/cards.md`
  (agregados `ServiceFAQManager` y el `ServiceOperationBoard` que faltaba del registro).
  Fases 4-6 (presentacion publica del detalle de servicio, wizard/checkout, limpieza de
  timeline) siguen pendientes — Fase 4 requiere confirmar antes la decision de color
  (ambar vs. violeta, Etapa 8 del plan).
- **Fix: paso 1 ("Servicio") del wizard de solicitud redundante con el detalle publico
  (2026-07-18, reportado por el usuario con HTML real de la pantalla):**
  `ServiceRequestWizard.vue` mostraba, al entrar desde `/servicios/{uuid}`, una pantalla
  ("Revisa los detalles y selecciona una opcion") que duplicaba integramente la info ya
  vista en el detalle (imagen, categoria/nivel, descripcion, features) y, en el caso comun
  de un servicio con 1 sola variante activa y 0 paquetes, no ofrecia ninguna decision real
  que tomar — el usuario solo veia la unica opcion ya auto-seleccionada y tenia que pulsar
  "Continuar" igual. **Fix:** `fetchService()` ahora trae la variante Y los paquetes en
  paralelo (`servicesService.detail()` + `.packages()`) y calcula si hay una decision real
  (`variantes activas > 1 OR paquetes.length > 0`); si no la hay, salta directo al paso 2
  ("Direccion") sin renderizar nunca el paso 1. Cuando SI hay una decision real que tomar
  (verificado con un servicio de prueba con 2 variantes + 1 paquete), el paso 1 se sigue
  mostrando pero **sin el panel de informacion duplicado** (imagen/badges/descripcion/
  features eliminados del wizard — esa info ya esta a un click via "Volver al servicio").
  Verificado con Playwright en ambos casos reales (el servicio exacto reportado por el
  usuario ahora aterriza directo en "Direccion y contacto"; un servicio con opciones reales
  sigue mostrando el selector, simplificado). Este fix ademas adelanta parte de la ETAPA 2
  ("simplificar formularios") del `PLAN_UNIFICACION_SERVICES_CON_RENTING.md`.
- **Fase 1-2 del Plan de Unificacion Services<->Renting EJECUTADAS (2026-07-17, pedido
  explicito "aplica acciones" tras aprobar el plan):** Fase 1 (verificacion tecnica) confirmo
  que los 6 managers admin genericos de Renting (`CatalogListManager`/`SeoManager`/
  `GalleryManager`/`DocumentsManager`/`VideosManager`/`SpecificationsManager`) NO son
  reutilizables tal cual — 5 de 6 no reciben `endpoint` como prop (URL fija en el archivo) y
  los 6 hardcodean el nombre del campo FK padre a `equipment`; decision aplicada: replicar el
  patron/shape REST exacto en el backend nuevo (no forkear ciegamente ni generalizar los 6
  archivos de Renting todavia, eso queda para la Fase 3 con confirmacion previa).
  Fase 2 (backend aditivo) completada: modelos `ServiceMarketing` (OneToOneField a
  `TechnicalService`, replica fiel de `renting.EquipmentMarketing` sin
  `purchase_price_reference`/`financial_message` ni campanas/testimonios) y `ServiceFAQ` (FK,
  replica de `RentalFAQ`) + 4 campos SEO en `TechnicalService` — migracion
  `0031_technicalservice_meta_description_and_more.py`. Nuevo
  `technical_services/services/marketing.py` (Commands/Selectors, mismos helpers privados
  que `renting/services/catalog.py`). Endpoints admin nuevos:
  `dashboard/services/{uuid}/marketing/` (accion en `AdminTechnicalServiceViewSet`) y
  `dashboard/service-faqs/` (`AdminServiceFAQViewSet` nuevo, mismo shape REST que
  `AdminRentalFAQViewSet` de Renting a proposito). `marketing`/`faqs`/campos SEO expuestos
  read-only en el `TechnicalServiceSerializer` publico, con `select_related`/`Prefetch`
  agregados a los 3 metodos de `ServiceSelector` para no repetir el bug de N+1 ya conocido de
  `get_variants()` en ese mismo serializer. Verificado: `manage.py check` limpio +
  `manage.py test technical_services dashboard` — 158/159, unica falla preexistente y no
  relacionada (mismatch `date` vs `string`, ya documentada en sesiones previas). Fases 3-6
  (tabs de admin, extraccion de componentes de presentacion publica, sidebar de resumen del
  wizard, migracion de timeline) quedan pendientes — requieren trabajo de frontend mas
  visible/riesgoso y una decision de color (ambar vs. violeta) que el plan deja explicita
  para confirmar antes de tocar UI. Todo documentado en el propio
  `PLAN_UNIFICACION_SERVICES_CON_RENTING.md` (seccion de estado al inicio + Etapa 4.3
  actualizada con el hallazgo real) y en `ARQUITECTURA_COMPLETA_SERVICES.md` (nuevo §16 C8).
- **Plan de unificacion Technical Services <-> Renting (2026-07-17, pedido explicito del
  usuario, SOLO documento, sin codigo):** entregable
  `technical_services/.AGENT/docs/PLAN_UNIFICACION_SERVICES_CON_RENTING.md`, producido tras
  auditoria comparativa real (3 agentes Explore) contra el codigo de ambos modulos, no
  suposiciones. Hallazgo central que reencuadra todo el plan: **Renting mismo no es un solo
  lenguaje visual** — tiene 2 familias internas (Detail: azul `#2563eb`/14-16px/patron
  "kicker+heading`, en `components/renting/detail/*`; Wizard/Cuenta: violeta `#7c3aed`/
  20-24px, en `components/customer/renting/*`+`RentalBookingWizard.vue`+`MyRentalsView.vue`).
  El wizard/checkout de Technical Services **YA esta alineado** al violeta de Renting-Wizard
  (comentario real en codigo: "Color violeta -- sistema unificado con alquiler") — el hueco
  real es la falta de un sidebar de resumen persistente durante el wizard (Renting si lo
  tiene). El catalogo/detalle de TS sigue en ambar `#d97706` (documentado como decision
  deliberada en su propia arquitectura, no un bug) — se recomienda mantenerlo como color de
  identidad y unificar solo la gramatica estructural (radios, sombras, patron kicker+heading,
  componentizacion), no forzar un unico color para todo el ecosistema.
  El detalle de servicio (`ServiceDetailView.vue`, 536 lineas monolitico, 0 subcomponentes)
  imita visualmente la estructura de bloques de `RentalDetailView.vue` (862 lineas, 13
  subcomponentes reales en `components/renting/detail/`) pero varios bloques son **stubs sin
  backend real**: video ("Video administrable pendiente"), antes/despues (sin binding de
  datos en absoluto), FAQ (fallback hardcodeado, sin modelo), reseñas (no existe seccion pese
  a que `ServiceReview` YA es un modelo real con datos). El dashboard/admin YA esta unificado
  a nivel de shell (`BaseOperationBoard.vue` compartido literalmente por
  `RentalOperationBoard.vue` y `ServiceOperationBoard.vue`, por diseño) — no hay Kanban en
  ningun de los dos modulos (el pedido original asumia uno que no existe en ninguno).
  Renting YA tiene un modelo de marketing real y maduro (`EquipmentMarketing`, OneToOne a
  `Equipment`, 15 campos) que sirve de patron fiel para el `ServiceMarketing` propuesto —
  pero ese modelo real de Renting NO tiene campanas con fecha ni testimonios (el FAQ vive en
  un modelo aparte `RentalFAQ`, el SEO vive directo en `Equipment`) — el plan recomienda
  replicar el patron real (sin campanas/testimonios, que serian una funcionalidad nueva para
  AMBOS modulos, no una adopcion de patron ya probado) en vez del listado de campos original
  del usuario. Documento entrega: comparacion completa, 8 componentes nuevos a extraer del
  monolito, verificacion pendiente de si los managers admin genericos de Renting
  (CatalogListManager/SpecificationsManager/etc.) son reutilizables sin fork, 6 fases de
  implementacion, checklists tecnico/UX/UI, riesgos, y restricciones explicitas (no
  cross-sell/up-sell/landing-personalizable — no existen en ningun modulo del proyecto hoy).
- **Re-auditoria de `technical_services` (2026-07-17, pedido explicito del usuario):**
  comparacion completa doc-vs-codigo del modulo (1877 lineas de
  `ARQUITECTURA_COMPLETA_SERVICES.md`, "Auditado: 2026-07-09", contra 30 migraciones reales
  y todos los archivos de `services/`/`api/`). Hallazgos principales (todos corregidos en
  el doc, ver §16 C7 del archivo para el detalle completo): (1) el motor de reglas de costo
  `ServiceCostRule`/`ServiceCostAssignment`/`ServicePricingCalculator`
  (`services/pricing.py`, mig. 0015) nunca se documento pese a ser un paso OBLIGATORIO de
  `ServiceSelector.get_variant_quotation()` desde hace tiempo — el descuento del cliente se
  aplica DESPUES de las reglas de costo, no sobre `labor_cost+material_cost` como decia el
  doc; (2) la Fase 7 de auto-asignacion real (`try_auto_assign_via_engine`, usa
  `TechnicianAvailabilityEngine`) ya esta en produccion (wireada en
  `confirm_slot_on_payment` + endpoint `POST /service-operations/{uuid}/auto-assign/`,
  cubierta por `AutoAssignViaEngineTestCase`) pero el doc la describia como "trabajo futuro,
  sesion con aprobacion propia"; (3) los 6 ViewSets de catalogo bajo `/api/v1/services/...`
  son `ReadOnlyModelViewSet`/`ViewSet` de solo lectura — el doc afirmaba que tenian
  `POST`/`PUT`/`DELETE` admin implementados ahi mismo (el CRUD real vive en
  `dashboard/api/views.py`); (4) Inventory/`StockRecord` es legado vestigial en este modulo
  (la disponibilidad real usa `ServiceBooking`/`is_active`, no stock) pero el Resumen
  Ejecutivo lo presentaba como el mecanismo vigente; (5) `api/internal_ai.py` (endpoint
  interno solo para el AI Core) no estaba documentado en absoluto.
  **Bug real corregido:** `ServiceRequestAdditionalCost.__str__` (`models.py`) referenciaba
  `self.name`, campo que no existe (el real es `name_snapshot`) — `AttributeError`
  garantizado en cualquier `str()` de una instancia. **Gap real cerrado:** los templates de
  notificacion `service_request_created`/`service_status_updated` (usados desde siempre por
  `ServiceCommands`) nunca tuvieron migracion de seed a diferencia de los demas templates
  del modulo — existian en la BD de dev solo porque alguien los creo manualmente; en un
  entorno nuevo ambas notificaciones fallarian en silencio para siempre. Cerrado con
  `migrations/0030_seed_service_request_status_templates.py` (valores identicos a los
  reales en dev, aplicado como no-op ahi). **Gaps documentados pero NO cerrados en esta
  pasada (requieren decision/alcance propio):** `ServiceConfiguration` no tiene NINGUN
  endpoint de escritura en todo el proyecto (Commands existen, ninguna URL los expone); el
  FSM completo de `ServiceOperation` (~13 endpoints: plan/assign/reschedule/cancel/etc.)
  tiene CERO tests directos en las 3 suites de la app. Verificado con
  `manage.py test technical_services`: 107/108 (1 falla pre-existente y no relacionada,
  `test_serializer_accepts_richer_request_metadata`, un mismatch de tipo `date` vs `string`
  en una aserccion, no causada por este audit). Tambien actualizado
  `technical_services/CLAUDE.md` (tabla "Archivos clave" tenia 6 archivos `services/`+
  `api/` reales sin listar: `calendar.py`, `operations.py`, `packages.py`, `pricing.py`,
  `availability_views.py`, `operation_views.py`, `package_serializers.py`,
  `internal_ai.py`, `signals.py`).
- **Sincronizacion con `docker-compose.prod.yml` (2026-07-17):** verificado — el compose de
  produccion NO necesita ningun cambio por la unificacion de "Mi Cuenta" (ver entrada
  siguiente). El servicio `frontend` (Vite dev server) explicitamente NO existe en
  produccion (comentario propio del archivo, linea 12-16): el bundle de Vue se compila
  DENTRO de la imagen `django` via el stage `frontend-builder` del `Dockerfile`
  (`COPY --from=frontend-builder /app/dist /code/static/panel/js/bundle`), que corre
  `npm run build` fresco contra TODO `ecommerce_sintel/frontend/` en cada build de imagen.
  Esto significa que las 8 vistas + libreria de componentes nuevas de "Mi Cuenta" quedaran
  incluidas automaticamente la proxima vez que se reconstruya la imagen `django` de
  produccion — no hace falta editar `docker-compose.prod.yml`, `Dockerfile` ni agregar
  ningun servicio. **Sync a produccion pedido, NO ejecutado** (regla ya establecida: nunca
  elevar a produccion sin instruccion explicita, ver `.AGENT.md`). Cuando se autorice, el
  comando es el ya documentado en sesiones previas:
  `docker compose -f docker-compose.prod.yml --env-file .env.production build --no-cache django`
  seguido de `up -d` y, por el bug ya conocido de DNS stale tras recrear django,
  `docker restart sintel_prod_nginx`.
- **Unificacion del Customer Dashboard / Design System de "Mi Cuenta" (2026-07-17, pedido
  explicito del usuario, plan completo aprobado):** los 8 modulos de "Mi Cuenta" (Perfil,
  Pedidos, Operaciones, Wishlist, Direcciones, Metodos de Pago, Cotizaciones, "Solicitar
  cuenta como Asociado de Negocio") estaban construidos en sesiones distintas, cada uno con
  su propia version de card/badge/empty-state/skeleton/overlay con micro-variaciones
  (padding 18/20/24px, 2 gradientes de skeleton distintos, 2 nombres de clase para el mismo
  overlay, Cotizaciones sin sidebar y con markup de header totalmente distinto).
  **Fix:** nueva libreria de 13 componentes compartidos en
  `frontend/src/components/customer/account/` (`CustomerAccountShell`, `CustomerPageHeader`,
  `CustomerCard`, `CustomerStatusBadge`, `CustomerEmptyState`, `CustomerErrorState`,
  `CustomerSkeleton`, `CustomerButton`, `CustomerConfirmInline`, `CustomerOverlayPanel`,
  `CustomerDetailRow`, `CustomerSection`, `CustomerAvatar`, `CustomerPagination`),
  registrada en `ai_skills/frontend/components/cards.md` seccion 4.0. Los 8 modulos
  reescritos para consumirla; no se construyo un Timeline nuevo (se reutilizo
  `components/shared/StatusTimeline.vue`, ya unificado desde antes).
  **Decisiones de producto confirmadas con el usuario antes de ejecutar:** "Conviertete en
  Profesional" NO se elimino (es un flujo real y completo: `auth/request-upgrade/` + KYC de
  5 documentos + aprobacion admin + marketplace) — se re-marco en el mismo lugar
  (`ContractorOnboardingWizard.vue`, misma ruta `perfil-profesional`/`contractor-onboarding`)
  como "Solicitar cuenta como Asociado de Negocio", agregandole una pantalla de
  onboarding-hub (Estado actual/Progreso/Requisitos/Pasos pendientes/Observaciones del
  admin, reutilizando `GET auth/verification/` ya cargado) ANTES del wizard de 4 pasos
  existente, que sigue intacto. "Notificaciones" (`CustomerNotificationsView.vue`) SI se
  elimino por completo (componente, ruta `customer-notifications`/`notificaciones`, link
  del sidebar) — confirmado explicitamente por el usuario, no era codigo muerto.
  **Bugs reales encontrados y corregidos durante la verificacion (no reportados, hallados
  con Playwright):** `CustomerQuotesView.vue` llamaba `quotes/` (raiz del router DRF, con
  multiples sub-recursos) en vez de `quotes/quotations/` — devolvia 200 con un indice de
  hyperlinks en vez de la lista, y `v-for` sobre ese objeto iteraba sus valores (strings) en
  vez de tronar, produciendo un `TypeError` silencioso atajado por el `ErrorBoundary` (ver
  `.AGENT.md` sec. 18.13); Wishlist no tenia NINGUNA confirmacion al eliminar (ahora usa
  `CustomerConfirmInline`); Metodos de Pago usaba `confirm()` nativo (ahora tambien
  `CustomerConfirmInline`); Cotizaciones y Operaciones no mostraban el `AccountSidebar` en
  absoluto (outliers estructurales reales, ahora corregidos).
  **Verificado con Playwright** (usuario CUSTOMER real, KYC bootstrapeado con
  `KycCommands.bootstrap_approved` para pasar el gate de login) contra los 8 modulos:
  sidebar visible en los 8, cero errores de consola, cero overflow horizontal en desktop y
  375px, `window.confirm` interceptado y confirmado que NUNCA se invoca. Sin cambios de
  backend en todo este fix (excepto los 2 fixes de endpoint/UX de frontend arriba).

- **Fix "Mis Direcciones" 404 + sincronizacion con la direccion del registro (2026-07-17,
  pedido explicito del usuario):** `Mi Cuenta > Mis Direcciones` (`CustomerAddressView.vue`)
  llamaba `orders/shipping-addresses/` en sus 4 requests (list/create/set-default/delete) y
  recibia 404 en todas — causa raiz simple: `orders/api/urls.py` registra
  `router.register(r'addresses', ShippingAddressViewSet, basename='shipping-address')`, la
  URL real es `orders/addresses/`; el `basename` de un router DRF solo nombra el reverse-URL
  interno, nunca aparece en el path (ver `.AGENT.md` sec. 18.12). Ademas, la direccion
  capturada durante `/register` (constructor colombiano tipo de via/numero/generadora/placa)
  nunca llegaba a `orders.ShippingAddress` — solo se guardaba en `UserProfile.address`/
  `.city`/`.country` — obligando a re-escribirla. `orders.ShippingAddress` YA era el modelo
  oficial y completamente conectado (Checkout ya exige `shipping_address_uuid` de ahi); no
  se creo ningun modelo nuevo, solo se cerro el puente que faltaba.
  **Fix backend:** campo nuevo `label` en `ShippingAddress` (migration 0015); nueva clase
  `ShippingAddressCommands` (Service Layer que antes no existia para este modelo, con
  `create()`/`update()`/`set_as_default()`) que garantiza SIEMPRE "solo un default por
  usuario"; `ShippingAddressViewSet` ahora delega a los Commands + nuevo action
  `set-default`; `accounts/services/commands.py` gano
  `_create_default_shipping_address_from_registration()`, llamado desde AMBOS
  `register_user()` y `create_from_verified_payload()` justo despues de crear el
  `UserProfile`, reutilizando los mismos datos ya capturados en el registro (nunca se piden
  de nuevo). De paso se corrigieron 2 bugs preexistentes encontrados por los tests nuevos:
  `ShippingAddressSerializer.validate()` no respetaba `self.partial` (un `PATCH` con solo
  `{"is_default": true}` fallaba con 400 exigiendo los demas campos), y
  `ShippingAddressSelector.LIST_FIELDS` no cubria 4 columnas que el serializer si expone
  (N+1 por recarga de campo diferido en cada fila listada).
  **Fix frontend:** las 4 llamadas corregidas a `orders/addresses/`; campo `label` agregado
  al formulario (titulo de card); `confirm()` nativo reemplazado por confirmacion inline
  (`pendingDelete` + `.addr-confirm-delete`, mismo patron `bg-danger-subtle` que
  `UserList.vue` — el proyecto prohibe dialogs nativos).
  **Fuera de alcance, diferido explicitamente:** pre-rellenar la direccion principal en los
  wizards independientes de Renting/Quotes/Technical Services (cada uno captura direccion
  inline en su propio flujo ya aprobado en sesiones anteriores).
  **Verificado:** `orders.tests.ShippingAddressBookTestCase` (4 tests) +
  `RegistrationCreatesDefaultShippingAddressTestCase` (1 test), suite `orders`/`accounts`/
  `kyc` completa sin regresiones nuevas, y de punta a punta con Playwright contra el dev DB
  real: registro con direccion estructurada -> aparece de inmediato en
  `/mi-cuenta/direcciones` marcada "Direccion Principal" sin re-pedirla; crear 2da direccion
  + "Seleccionar como direccion de envio" -> la 1ra pierde el badge de default; eliminar via
  la confirmacion inline. Datos de prueba desechables eliminados al terminar. Detalle
  completo en `orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md`
  (Historial de Cambios, 2026-07-17).
- **Fix HTTP 500 al eliminar usuarios (2026-07-17, pedido explicito del usuario, auditoria
  de 9 fases):** `DELETE /api/v1/users/{uuid}/erase/` hacia `user.delete()` (HARD delete)
  directo en `UserViewSet.erase()`, violando la regla ya establecida del proyecto
  (`.AGENT.md` sec. 6.1: nunca DELETE fisico, usar `is_deleted`). Causa raiz REAL
  (reproducida de forma segura con `transaction.atomic()`+rollback forzado sobre la cuenta
  real que fallaba, `ceo@sintel.net.co`): **ninguna** FK directa a `User` usa
  PROTECT/RESTRICT, pero `RentalOperation.rental_request` (PROTECT) choca dos saltos mas
  abajo cuando el hard-delete de User cascade-borra su `RentalRequest` (CASCADE) --
  `django.db.models.deletion.ProtectedError` sin capturar -> 500. Mismo patron tambien
  posible via `technical_services.ServiceOperation.order` (PROTECT sobre `Order`, tambien
  CASCADE desde User) -- 2do punto de choque encontrado en la auditoria, nunca disparado
  aun pero con el mismo riesgo. Auditoria completa: ~26 FKs `CASCADE` mas hacia `User`
  (Orders, Payments, Reviews, Chat, etc.) que un hard-delete real hubiera borrado en
  cascada o abortado a medias -- perdida de datos de negocio real.
  **Fix:** nuevo `UserCommands.erase_user()` (`users/services/commands.py`) hace
  soft-delete real (`user.is_deleted = True`, nunca `.delete()`) -- `UserSelector.list_all()`
  ya filtraba `is_deleted=False` (patron `SintelBaseModel` de las otras 16 apps), asi que el
  usuario desaparece de `/panel/usuarios` sin tocar ninguna fila relacionada. Esto elimina
  la clase de bug entera (no solo el caso de `RentalOperation`) sin necesidad de tocar
  ninguno de los ~28 modelos relacionados auditados. `UserViewSet.erase()` simplificado a
  llamar el Command + un `except (ProtectedError, IntegrityError)` de defensa (409) por si
  a futuro se reintroduce un hard-delete en otro lado. Frontend (`UserList.vue`) no
  necesito cambios -- ya mostraba `err.response?.data?.detail` correctamente, solo nunca
  lo recibia limpio. 7 tests nuevos en `users/tests.py::UserEraseTestCase` (incluye
  recrear el caso real con `RentalRequest`+`RentalOperation` y confirmar que sobreviven
  intactas). Un test PRE-EXISTENTE (`UserViewSetAuditLogTestCase.test_erase_logs_...`)
  esperaba el HARD-delete viejo (`User.objects.filter(...).exists()` False) -- actualizado
  para reflejar el nuevo contrato (fila sigue existiendo, `is_deleted=True`). Verificado
  con una reproduccion real via `Client(SERVER_NAME='localhost')` contra la BD de dev
  (patron ya establecido, sin persistir tokens JWT reales): 204 en vez de 500,
  `RentalRequest`/`RentalOperation` de prueba intactas tras el erase.
- **Correccion obligatoria del flujo de validacion de Registro (2026-07-17, pedido explicito
  del usuario):** antes, `submitStep1` en `RegisterView.vue` ya llamaba `validateStep1()`
  antes del POST a `register-request/` (el gate en si ya existia), pero la validacion
  MISMA tenia huecos reales: password solo chequeaba longitud>=12 (no mayuscula/minuscula/
  numero/especial, pese a que `PasswordStrengthMeter` los MOSTRABA visualmente sin
  bloquear el submit), email no validaba formato (solo "no vacio"), nombre/apellido no
  validaban longitud. Ademas el `<form>` del paso 1 no tenia `novalidate`, asi que un
  campo vacio podia disparar el popup nativo del navegador en vez del mensaje inline de
  la app. **Fix:** nuevas funciones compartidas en `kycValidation.js`
  (`isValidEmail`, `validatePasswordComplexity` — mismos criterios que
  `PasswordStrengthMeter.vue`/`ecommerce/validators.py::ComplexPasswordValidator`),
  validacion de longitud de nombre/apellido (min 2 - max 50, espeja
  `kyc/models.py::UserVerification.primer_nombre` max_length=50), `novalidate` en el
  form, y auto-scroll+foco al primer campo invalido si la validacion falla (el grid de 2
  columnas puede dejar un error fuera de la vista). Verificado: un formulario invalido
  (email sin arroba + password debil) NO dispara ninguna peticion a `register-request/`;
  un formulario completamente valido sigue funcionando de punta a punta con codigo OTP
  real.
- **Bugs post-Fase-5 encontrados por el usuario y corregidos (2026-07-17):**
  1. **Bug real de regresion:** `ToastManager` (`components/layout/ToastManager.vue`) solo
     se monta en `CustomerLayout.vue` y `AppShell.vue`. Al mover `/login`, `/register`,
     `/forgot-password` fuera de esos shells (Fases 2-3), CUALQUIER `toast.success()`/
     `toast.error()` en esas 3 paginas quedo silenciosamente sin efecto (el estado
     compartido de `useToast()` se actualizaba pero nada lo renderizaba). Sintoma
     reportado por el usuario: "no permite crear el usuario despues de ingresar el
     codigo" — en realidad SI fallaba correctamente (telefono duplicado con otra
     cuenta real, `ceo@sintel.net.co`), pero el usuario nunca via el toast que lo
     explicaba. **Fix:** agregado `<ToastManager />` a `CustomerAuthLayout.vue` (un
     solo lugar arregla Login+Registro+ForgotPassword de una vez, ya que las 3 usan
     ese layout compartido).
  2. **Mejora de UX pedida explicitamente:** el conflicto de telefono/email duplicado en
     `RegisterView.vue::submitStep2` ahora ADEMAS del toast setea `errors.phone_number`/
     `errors.email` (borde rojo + texto persistente, mismo patron que el resto del
     formulario) y mueve el foco automaticamente al campo exacto al volver al paso 1 —
     ya no depende solo de un toast de 4s que se puede perder.
  3. **Direccion estructurada pedida explicitamente:** el campo unico "Direccion *" en
     `PersonalInfoFields.vue` (usado solo por `RegisterView.vue`) se reemplazo por el
     mismo constructor de direccion colombiana ya usado en
     `views/customer/renting/RentalBookingWizard.vue` (tipo de via + numero + generadora
     + placa + complemento opcional, con vista previa en vivo) — reutiliza
     `COLOMBIAN_ROAD_TYPES` de `@/data/colombiaLocations.js`, arma el mismo formato de
     string ("Calle 31 Bis # 68 I - 38, complemento") y lo sincroniza a `form.direccion`
     via `watch()`, igual que el wizard de renta. Verificado end-to-end con codigo OTP
     real: `UserProfile.address` queda guardado con el formato correcto.
  - **Tecnica de verificacion reutilizada:** handoff por archivo marcador (Playwright en
    el contenedor frontend espera un archivo; el host escribe el codigo real leido de la
    BD) para probar flujos completos con OTP real pese a que frontend/backend viven en
    contenedores separados sin acceso cruzado.
- **Rediseno de autenticacion, Fase 5 COMPLETA — PROYECTO CERRADO (2026-07-17):** pulido
  transversal final sobre las 5 vistas (`LoginView`, `RegisterView`, `ForgotPasswordView`,
  `AdminLoginPage`, `AdminForgotPasswordView`) + `OtpInput.vue`. Accesibilidad: `role="alert"`
  + `aria-live="polite"` en todas las alertas de error, `aria-label` en botones
  mostrar/ocultar contraseña y en cada casilla de `OtpInput`, foco automático al cambiar de
  paso (`watch(step, ...)` con `setTimeout(260ms)` para esperar la transición de salida),
  autofocus del primer campo al montar. Animaciones: fade+leve-elevacion (.35s, respeta
  `prefers-reduced-motion`) al montar `CustomerAuthLayout`/`AdminAuthLayout`, sin dependencia
  nueva. Responsive: 0px de overflow horizontal verificado en 375/768/1440px en las 5
  vistas. **Verificación final end-to-end con código OTP real** (resuelto el problema de
  dos-contenedores de las fases anteriores con un handoff por archivo marcador: el script
  Playwright espera un archivo, un poll desde el host lo escribe con el código leído de la
  BD) — flujo cliente completo (`/forgot-password` → código real → nueva contraseña →
  auto-login a `/tienda`) y flujo admin completo (`/panel/forgot-password` → código real →
  nueva contraseña → auto-login a `/panel/dashboard`) confirmados exitosos de punta a punta.
  **Con esto el Plan Maestro de Modernizacion del Sistema de Autenticacion (5 fases) queda
  100% completo.** Ver plan completo en `C:\Users\Administrator\.claude\plans\enumerated-zooming-bubble.md`.
- **Rediseno de autenticacion, Fase 4 COMPLETA (2026-07-17):** `AdminAuthLayout.vue` nuevo
  (deliberadamente sin compartir nada con `CustomerAuthLayout.vue` — regla de separacion
  absoluta), tema oscuro tomado del sidebar del panel (`#0a0a0a` + gradiente
  `#fff→#38bdf8`), sin panel de marca/ventas. `AdminLoginPage.vue` rediseñado conservando
  intacto su `adminAuthClient` axios aislado (nunca `useApi`/`useAuth`). Nueva
  `AdminForgotPasswordView.vue` (4 pasos, mismo patron que la de cliente pero con cliente
  axios propio hacia `admin-auth/...`), reutiliza `OtpInput.vue`/`PasswordStrengthMeter.vue`
  (permitido por el spec: son utilidades de bajo nivel, no pantallas compartidas). Ruta
  `/panel/forgot-password` nueva. **Decision final sobre el split de `useAuthStore`
  (diferida en Fase 2): se confirma que NO hace falta** — ni el login admin ni su
  forgot-password necesitan estado separado, el aislamiento por getters+guard de hostname
  ya es suficiente; se retira del roadmap. Verificado con Playwright: tema oscuro
  confirmado (`rgb(10,10,10)`), sin panel de marca, login real funcionando (redirect a
  `/panel/dashboard`), flujo forgot-password completo (request→OTP con backend real,
  codigo incorrecto rechazado 400 sin avance).
- **Rediseno de autenticacion, Fase 3 COMPLETA (2026-07-17):** `ForgotPasswordView.vue`
  nueva, 4 pasos (email → OTP via `OtpInput` reutilizado → nueva contraseña con
  `PasswordStrengthMeter` reutilizado → éxito+auto-login), ruta `/forgot-password`
  registrada (top-level, junto a `/login`/`/register`), `LoginView.vue` actualizado a
  named route. Reenvío de código reutiliza el mismo endpoint `forgot-password-request`
  (no hay endpoint de resend separado en el backend) con cooldown de 60s solo en cliente.
  Verificado: build limpio, layout correcto (sin navbar, panel de marca, stepper de 4
  puntos), flujo request→OTP con respuesta real 200 del backend, y verify rechazando
  correctamente un código inválido/reciclado (400, sin avance erróneo) — el camino feliz
  completo (con código real) ya estaba cubierto por los tests automáticos de Fase 1
  (`CustomerForgotPasswordTestCase`), que corren en el mismo proceso que la BD y no tienen
  el problema de dos-contenedores que sí tiene un Playwright real con código real.
  **Hallazgo de infraestructura durante la verificación**: `EMAIL_BACKEND` en dev apunta a
  SMTP real (`smtp.gmail.com`), no console backend — cada request que envía OTP tarda
  ~3s (el envío de correo es síncrono dentro de la request). Nada que corregir (ya está
  en un `try/except` que no rompe la request), pero cualquier test/Playwright futuro
  contra estos endpoints debe esperar con `waitForSelector`/timeout generoso, no un
  `waitForTimeout` corto.
- **Rediseno de autenticacion, Fase 2 COMPLETA (2026-07-17):** Login+Registro cliente
  rediseñados. Nuevos: `frontend/src/components/auth/OtpInput.vue` (extraido de
  RegisterView, reutilizable), `CustomerAuthLayout.vue` (variant `split` para Login con
  panel de marca, `wide` para Registro sin el). `register` paso de child de
  `CustomerLayout` a top-level (ver `frontend/CLAUDE.md`, nueva excepcion documentada).
  Registro reagrupado en 3 cards (Personal/Contacto/Seguridad) + stepper de 3 pasos (se
  agrego una micro-pantalla de exito de 1.4s ya que solo habia 2 pasos reales). Login gano
  Recordarme (checkbox real: localStorage vs sessionStorage, cambio pequeño y aditivo en
  `store/auth.js`+`useAuth.js`+`useApi.js`+guard de hostname en `router.js` -- CUIDADO:
  `useApi.js` leia/escribia tokens DIRECTO de `localStorage` bypaseando el store, tuvo que
  parchearse tambien o "Recordarme" desmarcado rompia toda request autenticada) y deteccion
  de Caps Lock. **Split completo del Pinia store diferido** (29 archivos dependen de
  `useAuthStore` directo, desproporcionado para un rediseño visual) -- revisar en Fase 4 si
  realmente hace falta. Snapshot de Playwright `/login` regenerado intencionalmente. Enlace
  "¿Olvidaste tu contraseña?" apunta a `/forgot-password` (path literal, no named route) --
  la Fase 3 debe registrar esa ruta.
- **Rediseno de autenticacion, Fase 1 COMPLETA (2026-07-17):** infraestructura backend de
  "olvide mi contrasena" para cliente (`accounts`) y admin (`users`), 100% aislados entre
  si, reutilizando `EmailVerificationCode`/`VerificationCommands` (nuevo campo `purpose`:
  `registration`/`password_reset_customer`/`password_reset_admin`). Nuevas clases
  `CustomerPasswordResetCommands` (accounts) y `AdminPasswordResetCommands` (users, mismo
  archivo que `VerificationCommands` para no tocar el `admin_auth.py` marcado "NO
  MODIFICAR"). 6 endpoints nuevos (3 cliente en `AccountViewSet`, 3 admin en nuevo
  `users/api/admin_password_reset.py`), 6 tests nuevos, todos verdes. Roadmap completo
  (Fases 2-5, frontend) en `Documentacion/` o preguntar por "Plan Maestro de Modernizacion
  del Sistema de Autenticacion". Plan de fases: backend primero (Fase 1) -> Login+Registro
  cliente -> Forgot Password cliente UI -> Login admin + Forgot Password admin UI -> pulido
  transversal (accesibilidad/animaciones).
  - **Hallazgo critico de infraestructura de testing** (ver `.AGENT.md` sec. 18.9):
    `manage.py test` SIN argumentos excluye silenciosamente las apps `accounts` y `users`
    del discovery (94 tests nunca ejecutados por el chequeo "completo" estandar del
    proyecto) — esto invalida retroactivamente la confianza depositada en el "384 tests, 3
    fallos conocidos" usado el mismo dia para el despliegue a produccion. Verificar SIEMPRE
    `accounts`/`users` por separado (`manage.py test accounts`, `manage.py test users`)
    hasta que se corrija la causa raiz (probable colision de nombre de subpaquete
    `services/` compartido entre apps).
  - **2 bugs preexistentes encontrados** (no relacionados, no corregidos, ver `.AGENT.md`
    sec. 18.9 para el detalle): `NameError` en
    `accounts/services/commands.py::AvailabilityCommands.update_slot_status`; constante
    `ServiceVariant.CONTRACTOR_RATES` inexistente referenciada por un test.

- **Auditoria completa `AUDITORIA/12_CHECKLIST_IMPLEMENTACION.md` (2026-07-17):** Se
  verifico item por item (SPRINT 0 a SPRINT 4 + VERIFICACION FINAL) contra el codigo real,
  no contra las marcas `[x]` preexistentes (varias resultaron incorrectas). Checklist ahora
  100% cerrado. Ver seccion 18 de `.AGENT.md` para las reglas permanentes derivadas de los
  bugs encontrados. Resumen de lo corregido en esta pasada:
  - **Salida de backend real en produccion** causada por imports stale tras un split previo
    de Commands/Selectors nunca completado (`core/api/internal_ai.py`, `core/api/views.py`,
    `core/audit_queries.py`, `dashboard/api/views.py` — 27 ocurrencias). Ver `.AGENT.md` 18.1.
  - `operations/services/commands.py::_try_update_contractor_review` truncado a mitad de
    archivo (try sin except, variable `review` indefinida) — reconstruido.
  - `accounts/api/serializers.py`: typo `ALLOWED_STATUS` -> `ALLOWED_STATUSES`.
  - `UserProfile.total_services_completed` sin setter chocaba con `.annotate()` del selector
    de contratistas — ver `.AGENT.md` 18.2.
  - `UserProfile` `UniqueConstraint(document_type, document)` no excluia strings vacios +
    `AccountViewSet.profile()` sin `instance=` en el serializer — ver `.AGENT.md` 18.3.
  - `WompiCommands.initialize_transaction` con `@transaction.atomic` de alcance completo
    borraba su propio audit trail al re-lanzar el error — ver `.AGENT.md` 18.4.
  - `CartCommands.remove_item` tenia firma/comportamiento desalineado de sus 0 callers reales
    (hard-delete vs. soft-delete esperado) — re-firmado a `(cart, item_uuid)` soft-delete.
  - **SPRINT 4 (frontend, autorizado explicitamente por el usuario a ejecutar sin checkpoints
    intermedios):** stores admin monoliticos partidos por dominio (`rentingAdmin/*`,
    `quotesAdmin/*`, `technicalServicesAdmin/*`), 4 servicios `useApi()` nuevos
    (`shopService`, `quotesService`, `servicesService`, `operationsService`),
    `StatusTimeline.vue`/`BaseOperationBoard.vue` compartidos (7 y 4 consumidores resp.),
    `useErrorHandler.js` nuevo (patron unico de manejo de errores, documentado en
    `frontend/CLAUDE.md`), de-minificado `RentalBookingWizard.vue`, limpieza de 7 archivos
    muertos + entry Vite huerfano.
  - Vista redundante de seleccion de paquete/variante eliminada de
    `ServiceDetailView.vue` (decorativa, boton "Comprar servicio" sin query params, cero
    funcionalidad real); el flujo de solicitud de servicio real y unico es el wizard de 4
    pasos (Servicio -> Direccion -> Fecha -> Pago) en `ServiceRequestWizard.vue`.
  - **Sincronizado a produccion (2026-07-17, mismo dia):** confirmado el pedido, se corrio
    la suite completa en dev primero (384 tests, solo los 3 fallos pre-existentes conocidos:
    orders 405, technical_services formato de fecha, core.tests.test_models_and_signals),
    luego `docker compose -f docker-compose.prod.yml build --no-cache django` (rehorna
    tambien el bundle de frontend via el stage `frontend-builder` del Dockerfile) + `up -d`
    + `docker restart sintel_prod_nginx` (DNS stale, ver `feedback_nginx_stale_dns_after_django_recreate`).
    Verificado: contenedores healthy, `https://sintel.net.co` y
    `https://api.sintel.net.co/api/v1/health/` responden 200 desde internet real.
    **Hallazgo aparte, no resuelto:** `.git` en la raiz del repo esta vacio (solo
    `info/exclude`, sin `HEAD`/`objects`/`refs`) — `git status` falla con "not a git
    repository". No bloquea el deploy (que es 100% Docker-image-based, no git-based en este
    proyecto) pero elimina la red de seguridad de control de versiones; investigar aparte.

## 4b. Historial Reciente y Tareas Actuales (Junio 2026)
- **Pipeline operations (2026-06-27):** El pago confirmado crea tickets idempotentes por tipo de item (`SHOP_DELIVERY`, `RENTAL`, `SERVICE`), incluso para ordenes mixtas. Se agregaron roles `TRANSPORTER`, `CONTRACTOR`, `ACCOUNTANT`, disponibilidad transaccional, API `/operations/tasks/`, consola admin y portal operativo mobile-first.
- **Leccion critica DRF (2026-06-27):** Los metodos con `@action` deben estar dentro del `ViewSet` registrado en `DefaultRouter`. Un `@action` dentro de una `APIView` compila, pero el router no lo registra y el frontend recibe 404. Caso real: `renting/rental-requests/{uuid}/process-payment/` fallaba porque `process_payment()` estaba indentado dentro de `RentalRequestListCreateAPIView`; se movio a `RentalRequestViewSet`.
- **Verificacion obligatoria para acciones custom:** confirmar indentacion en el `ViewSet`, `router.register(...)`, `lookup_field='uuid'`, y ejecutar `python -m py_compile app/api/views.py`.

## 5. Historial Anterior (Mayo 2026)
- **Adaptación AI:** Replicación de configuraciones IA para que `Antigravity` opere consistentemente en todos los módulos (renombrado y adaptación a `ANTIGRAVITY.md`).
- **Problema Actual en Revisión:** Se corrigió un bucle silencioso en los `Navigation Guards` del frontend que atrapaba a usuarios no administradores en la Landing Page. Se mejoró la reactividad de la Landing para mostrar el estado de sesión actual.
- **Hitos Anteriores:** 
  - **Alineación de Dashboard (Mayo 2026)**: Refactorización completa de `DashboardView.vue` integrando métricas de marketing (conversión) y alertas de inventario (stock estancado/agotado). Implementación de accesos rápidos y estandarización de identificadores UUID.
  - **Dictamen de Interacción (Mayo 2026)**: Recomendación técnica aprobada para la transición de modales clásicos a patrones **Offcanvas** en la gestión de datos administrativos, priorizando la preservación de contexto y ergonomía móvil.
  - Estabilización de flujos de actualización en Facturas y Gastos (Contabilidad).
  - Integración de módulos Inventario y Proveedores bajo la misma arquitectura contable.
  - Sincronización Fase 1 de Frontend-Backend (Centralización de API y Módulos Core).
  - Actualización masiva de documentación a "EN DESARROLLO".

---
*Nota para el Agente:* Antes de cualquier intervención, revisa este archivo y el `ANTIGRAVITY.md` del módulo correspondiente para mantener el contexto intacto.
