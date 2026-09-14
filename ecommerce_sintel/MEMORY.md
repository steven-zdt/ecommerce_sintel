# MEMORY.md - Memoria del Proyecto Sintel E-Commerce

**Estado Actual:** `EN DESARROLLO - DEVELOPMENT`

Este documento sirve como registro activo de la memoria del proyecto para asegurar la continuidad del contexto entre sesiones de desarrollo, alineado con las reglas globales establecidas en `.AGENT.md`.

**Paso 2 del flujo de consulta jerarquico** (ver `.AGENT.md` -> "FLUJO OBLIGATORIO ANTES DE MODIFICAR CODIGO"): leer este archivo justo despues de `.AGENT.md` y antes de entrar al doc de una app especifica. Para el estado detallado y actualizado app-por-app, ver `../Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` — el historial de abajo (Mayo-Junio 2026) no se ha actualizado con las fases posteriores (kyc, security, operations, dashboard, core, notifications, support, Cloudflare Tunnel, etc.), documentadas en ese archivo y no aqui.

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

- **DESPLIEGUE A PRODUCCION 2026-08-31:** `./deploy/backup.sh` (dump BD
  verificado: `sintel_db_20260831_110616.dump`) + `./deploy/deploy.sh` (build
  django `--no-cache` desde working tree + `up -d`). Prod quedo con TODO el
  trabajo Meta Business (FASE 1-10 Django) + auditoria docker. Migraciones
  aplicadas a la BD de prod: `notifications.0008_metawebhookevent`,
  `0009_seed_purge_meta_webhook_events_task` (aditivas, verificadas). Tabla
  `MetaWebhookEvent` viva, PeriodicTask `purge-meta-webhook-events` sembrada.
  Imagen `ecommerce_sintel_ai:prod` reconstruida aparte (deploy.sh solo hace
  `django`) -> `sintel_prod_ai` recreado, healthy, `mcp_client` importa,
  `rag_ready:false` (ChromaDB no esta en prod, degradacion pre-existente
  esperada). Todo el stack `sintel_prod_*` healthy, HTTPS via nginx -> 200.
  MCP sigue dormido (`MCP_META_ADS_ENABLED=false`, sin META_APP_ID).
  Hallazgo durante el deploy: `pip install -r requirements.txt` del ai_engine
  fallaba transitoriamente por el backtracking de pip sobre `sse-starlette`
  (dep de mcp) -> se pineo `mcp==1.24.0` + `sse-starlette>=3.0,<3.1` en
  `ai_engine/requirements.txt`.

- **Auditoria imagenes Docker (2026-08-31):** ambas imagenes construyen y arrancan
  OK (Django `/api/v1/health/` -> db/redis/celery true, 258 migraciones aplicadas;
  ai_engine `/health` -> llm+rag ready, 21 manifiestos, `mcp_client` importa,
  `/data/mcp` escribible). Corregido:
  - `ai_engine/.dockerignore` -- NO existia -> la imagen horneaba `.AGENT/` (docs),
    `e2e_*`, `__pycache__`, `.pytest_cache` (capa /app 26M -> 5.5M). **Se MANTIENEN
    a proposito** `PROJECT_MAP.json` / `KNOWLEDGE_GRAPH.json` / `AI_MANIFESTS/` /
    `APP_MEMORY/` -- ai_manifest.py/memory_builder.py/specialized_retrieval.py los
    leen desde `/app` en runtime.
  - `Dockerfile` (Django): frontend `npm install` -> `npm ci` (build reproducible;
    lockfile verificado en sync).
  - `ecommerce_sintel/.dockerignore` es un stub inerte -- el que aplica al build de
    Django es `../.dockerignore` (raiz del repo); el de sintel_ai es
    `ai_engine/.dockerignore`.
  - Tras agregar un `.dockerignore` nuevo, `docker compose build` reusa la capa
    `COPY` vieja -> hace falta `docker compose build --no-cache <servicio>` una vez.
  Pendiente (no critico): ai_engine corre como root (Django si tiene user `sintel`);
  el `Dockerfile` de Django hace `poetry lock` dentro del build (ignora el
  poetry.lock commiteado, que ademas esta stale sin `cryptography`); `sintel_ollama`
  tiene reserva GPU nvidia dura (falla `up` en host sin GPU).

- **Integracion Meta Business -- FASE 1-4, 6, 6.1, 7, 9, 10 COMPLETAS (2026-08-31):**
  plan maestro de 26 fases en
  `../Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md`
  (FASE 0 = inventario de credenciales, bloqueada en el usuario; FASE 5 ya
  cumplia; FASE 8 = dashboard BFF + Vue; FASE 11-26 = capabilities/policy/
  human-approval de writes, Conversions API, catalogo, IG/FB, observabilidad,
  audit trail, canary -- PENDIENTES).
  Implementado (aditivo; `manage.py test marketing` 57 OK, `notifications` sin
  regresiones, `ai_engine pytest tests/` 158/16):
  - Nuevo paquete `marketing/integrations/meta/` = frontera HTTP UNICA hacia
    `graph.facebook.com`. `MetaGraphClient` (transporte puro, patron
    `WompiApiClient`: `get/post/delete/paginate`, clasificacion de errores
    429/auth/transient/config), `signatures.verify_meta_webhook_signature()`
    (funcion pura fail-closed), `MetaWhatsAppClient`.
  - `notifications/clients/whatsapp.py` reducido a shim:
    `class WhatsAppClient(MetaWhatsAppClient)` + alias de excepciones
    (`WhatsAppApiError=MetaApiError`, etc.). Nueva dependencia permitida:
    `notifications` importa de `marketing.integrations.meta`.
  - Config de activos Meta = `settings`/`.env` + `OrganizationSelector.
    get_integration_settings()` extendido (`META_GRAPH_API_VERSION`,
    `META_BUSINESS_ID`, `META_WABA_ID`, `META_AD_ACCOUNT_ID`, `META_CATALOG_ID`,
    `META_PIXEL_ID`, `META_DATASET_ID`). NADA en BD (regla de `organization`).
  - Modelo `notifications.MetaWebhookEvent` (migracion `0008`): auditoria de cada
    evento del webhook Meta (incl. `REJECTED` por firma y `DUPLICATE` por
    reintento). `whatsapp_webhook.py` lo persiste + tambien registra callbacks
    `statuses` (delivered/read/failed). `process_whatsapp_inbound_task` gana
    `event_id` opcional y marca el ciclo de vida. Purga: migracion `0009` siembra
    `notifications.purge_meta_webhook_events` (diaria, sanitiza payload a 30d,
    borra a 180d).
  - FASE 4: `marketing/channels/{whatsapp,facebook,instagram}_channel.py`
    migrados a `MetaGraphClient` / `MetaWhatsAppClient` (interfaz `send()` intacta).
  - FASE 7: `marketing/integrations/meta/marketing.py::MetaMarketingClient`
    (solo GET: campaigns/adsets/ads/insights/account_summary) +
    `marketing/services/meta_selectors.py::MetaCampaignSelector` (normaliza).
  - FASE 9: `marketing/api/internal_ai.py` +4 vistas Meta READ
    (`AiMetaCampaignsView`/`...CampaignDetailView`/`...InsightsView`/
    `...AccountSummaryView`, `IsAdminUser`), registradas en
    `ecommerce/internal_ai_urls.py` bajo `marketing/meta/...`. `MetaConfigError`
    -> HTTP 503, resto de errores Meta -> 502.
  - FASE 10: `ai_engine/mcp_client/` (NO `mcp/` -- ensombreceria el SDK `mcp`):
    `MetaAdsMCPClient` (protocolo MCP + OAuth PKCE hacia
    https://mcp.facebook.com/ads, MCP oficial de Meta lanzado 2026-04-29),
    `policy.py` (READ-only en F10), `storage.py` (FileTokenStorage -> volumen
    `*_mcp_tokens:/data/mcp`), `authorize.py` (CLI OAuth one-shot). `mcp>=1.24,
    <1.25` en requirements (>=1.25 rompe fastapi 0.115). Endpoints dev
    `GET/POST /api/v1/ai/mcp/{status,ping}`. **Falta:** `docker compose build
    sintel_ai` + `python -m mcp_client.authorize` (login del usuario en el
    navegador) + `MCP_META_ADS_ENABLED=true`. El LLM aun NO ve el MCP (F11-14).
  - **NO commiteado** (rama `fix/audit-p0-remediation` con mucho trabajo previo
    sin relacionar -- no hacer `git add` masivo).

- **Plan "CONFIGURACION DINAMICA DE MODELOS LOCALES PARA CHAT SUPPORT" -- FASE 0-5
  COMPLETO (2026-08-13):** nueva app `ai_provider` (modelos `AIProvider`/`AIModel`/
  `AIChannelConfig`/`AIChannelFallback`), admin editable desde
  `/panel/soporte/ia-config` sin tocar `.env` ni reiniciar Docker (dentro de la
  ventana de cache de 15s). Precedente seguido: `core/` app (`SingletonMixin`,
  Selectors/Commands, lectura publica vs escritura `dashboard/` admin-only).
  Cifrado de `api_key` en reposo construido desde cero (`shared/fields.py::
  EncryptedTextField`, Fernet -- no existia ningun mecanismo de cifrado en el
  repo). `ai_engine/llm_factory.py::get_dynamic_llm()` (nuevo, usado SOLO por
  `/chat`) consulta `GET /api/v1/internal/ai/provider-config/` (AllowAny --
  aislamiento de red, mismo patron que el resto de `/internal/ai/*`) y cae a
  `LOCAL_MODEL_CHAIN` si no hay config real -- `LOCAL_MODEL_CHAIN`/`_STATE['llm']`
  NO se tocaron (siguen alimentando `/generate`, AI Editor, fuera de alcance).
  **Hallazgo operativo real:** `sintel_ai` no tiene bind-mount de codigo
  (`.:/workspace:ro` es solo para indexar la KB) -- cualquier cambio en
  `ai_engine/` requiere `docker compose build sintel_ai` real, `--reload` nunca
  ve cambios del host. Validado end-to-end en vivo: chat real usando el
  provider dinamico (`[llm] /chat usando config dinamica`), fallback real al
  desactivar el provider, panel admin real (login+JWT real, crear/probar
  conexion/eliminar proveedor, todo contra el backend real). Tests: 24/24
  (`ai_provider`, incluye lectura SQL cruda confirmando que `api_key` nunca
  queda en texto plano), 12/12 (`ai_engine/tests/test_dynamic_llm_config.py`),
  0 regresiones (127/127 `ai_engine` completo, 76/77 Django -- el 1 "fallo" es
  la limitacion pre-existente de `support/tests.py` sin pytest instalado, no
  relacionado). Detalle completo fase por fase:
  `ai_provider/.AGENT/FASE1_MODELOS.md` a `FASE5_FRONTEND.md`, arquitectura en
  `ai_provider/.AGENT/docs/ARQUITECTURA_COMPLETA_AI_PROVIDER.md`.
- **Plan "FASE 61 -- AI MODEL QUALIFICATION" -- COMPLETO (2026-08-12):** benchmark real
  cross-stack del AI Editor. Regla nueva del usuario a mitad de campaña: Ollama NUNCA decide
  ediciones de codigo del proyecto (solo chatbot/soporte) -- ver
  `feedback_ollama_never_edits_code.md`. Caso real: `SocialLink.opens_in_new_tab` (organization),
  8 archivos backend+frontend. 8 gaps reales encontrados (A-H) en el grafo/mecanismo, 1
  corregido en codigo (GAP G, regex de `build_architecture_context()`, test de regresion,
  450/450). GAP H (el mas significativo): `OrganizationCommands.update_social_link()` nunca
  fue detectado como dependencia por el grafo -- causo el UNICO fallo real de la campaña
  (backend test FAIL en el intento 1), encontrado solo por ejecucion real de tests, corregido
  con 1 retry exitoso (19/19 tests). 5 ciclos reales de escritura contra WORKSPACE_ROOT
  (confirmados explicitamente uno por uno), reversion 100% exitosa y verificada (SHA-256 +
  git status + 0 registros huerfanos en la DB real) en cada uno. Clasificacion final (nunca
  fusionada): Ollama llama3.1:8b = LEVEL 2 en Change Intent, LEVEL 0 en generacion de patches
  (fallo real, 2 intentos, JSON invalido) -- mecanismo `ai_editor` + Claude como autor del
  patch = LEVEL 7 (cross-stack con tests y reconciliacion). Documentacion completa en
  `ai_editor/.AGENT/` (FASE61_0 a FASE61_22 + AI_MODEL_QUALIFICATION_REPORT.md +
  AI_MODEL_BENCHMARK.md + AI_EDITOR_CROSS_STACK_QUALIFICATION_FINAL.md).
- **Plan "AI Change Proposal Engine", FASE 54-55 -- COMPLETO, 60/60 fases (2026-08-12):**
  confirmado explicitamente por el usuario (3 pasos: origen manual del contenido, rollback
  inmediato, diff exacto). Unica escritura real contra WORKSPACE_ROOT de toda la sesion:
  comentario de 1 linea en core/services/commands.py (HomeCardGroupSelector.get_by_name).
  El archivo tenia trabajo real sin commitear del usuario (FeatureBanner*, HomeCardCommands) --
  verificado que no se solapaba con las lineas objetivo antes de proceder, comunicado y
  confirmado. review_and_promote(confirm=True) -> PROMOTED, verificado -> rollback_outcome() ->
  ROLLED_BACK, verificado con SHA-256 completo del archivo (hash identico antes/despues) y
  git diff (0 rastros). El trabajo pendiente del usuario quedo intacto. Plan "AI Change Proposal
  Engine" completo: 60/60 fases. Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md`
  seccion "FASE 54-55".
- **Plan "AI Change Proposal Engine", FASE 51-53 (2026-08-12):** autorizado tras check-in
  explicito (el plan se habia pausado a proposito en FASE 60 parcial dado que esto es una
  escalada de alcance real). Paquete nuevo ai_editor/agent/: AgentPolicy (FASE 52, solo
  max_retries/provider, sin flag de auto-promover -- esa capacidad no existe aca) +
  run_autonomous_change_loop() (FASE 51+53) que orquesta TODO generation/ (FASE 24-50) en una
  sola llamada. REGLA FINAL DE SEGURIDAD garantizada ESTRUCTURALMENTE (test AST: agent/ nunca
  importa generation.promotion/repository.promote) -- status maximo posible: APPROVAL_REQUIRED.
  Primera vez en las 60 fases que se corrio contra un LLM REAL: Ollama local SI esta alcanzable
  en este entorno (localhost:11434, llama3.1:8b) -- corrigio una afirmacion previa falsa de que
  ningun LLM estaba disponible (ver ai_editor/__init__.py, corregido). Hallazgo real: el modelo
  local de 8B no siempre produce JSON estructurado valido en pocos intentos (REJECTED correcto,
  no un bug del pipeline). 449/449 tests (441+8). 52 de 60 fases cubiertas. Solo faltan FASE 54-55
  (repo real), requieren confirmacion explicita del usuario en el momento. Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 51-53)".
- **Plan "AI Change Proposal Engine", FASE 56-60 parcial (2026-08-11):** cierre del batch
  autorizado por "continua todas las fases... hasta darla por terminada". performance.py mide
  timings reales de 6 etapas sin LLM (GENERATING_LLM siempre NOT_MEASURED, ningun LLM real se
  invoco en todo el plan). FASE 57-59: verificado que los 23 submodulos de generation/ tienen su
  test, 0 gaps, consolidacion sin construccion nueva. FASE 60 (parcial): tabla de readiness de
  FASE 24-50+56-59, todas REALES o marcadas NOT_IMPLEMENTED honesto -- NO cubre FASE 51-53 (AI
  Editor Agent, loop autonomo con tool-calling: escalada de alcance real, el propio prompt
  maestro la condiciona a "solo despues de que el Proposal Engine sea estable") ni FASE 54-55
  (prueba contra el repo REAL): ambas requieren decision/confirmacion explicita del usuario, no
  una continuacion automatica -- mismo criterio ya aplicado en FASE 38 (guardrail) y
  POST-GRAPH 21/22 (repo real). 441/441 tests. 49 de 60 fases cubiertas. Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` secciones "FASE 56"/"FASE 57-59"/"FASE 60".
- **Plan "AI Change Proposal Engine", FASE 47-50 (2026-08-11):** batch autorizado por "continua
  todas las fases... hasta darla por terminada". FASE 47: promotion.py::rollback_outcome() reusa
  repository.rollback.rollback_promotion() (POST-GRAPH 16) aceptando un PromotionOutcome directo.
  FASE 48: GenerationResult.provider/.model + audit_pipeline_run(proposal=, generation_result=)
  registran de que LLM salio cada propuesta, nunca contenido crudo (verificado con test dedicado).
  FASE 49 "Security Hardening": auditoria real de FASE 24-46 -- encontre y corregi 1 gap genuino:
  code_quality.py construia real_path sin el boundary check anti-traversal que patch/engine.py ya
  tiene (riesgo practico BAJO, ya mitigado aguas arriba por FASE 29, corregido igual por defensa
  en profundidad). Limites documentados (MAX_OPERATIONS_PER_PROPOSAL=20,
  MAX_PATCH_CONTENT_BYTES=5MB, MAX_SANDBOX_FILES=500, DEFAULT_MAX_RETRIES=3) verificados reales y
  activos. FASE 50: pipeline_states.py con los 15 estados nombrados por el prompt maestro +
  classify_pipeline_state() (clasificacion honesta sobre objetos reales, no una maquina de
  estados nueva; 3 de los 15 -- VALIDATING/SANDBOXED/APPROVED -- no tienen hoy un dato real que
  los distinga, documentado explicito). 437/437 tests (414+23). 45 de 60 fases cubiertas.
  Siguiente: FASE 51-53 (AI Editor Agent) requiere check-in explicito antes de construir (escalada
  de alcance real); FASE 54-55 (repo real) requieren confirmacion explicita aparte. Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 47-50)".
- **Plan "AI Change Proposal Engine", FASE 45-46 (2026-08-11):** human_review.py::
  render_full_review() compone 11 reportes opcionales en un texto de revision. promotion_gate.py::
  check_promotion_gate() consolida Reconciliation/Impact/Architecture como bloqueantes, Contract
  como warning; "tests pass" queda NO VERIFICABLE honesto. No reemplaza review_and_promote()
  (decision/confirm siguen obligatorios). Encontre (no bug, confusion de tipos real) que
  confidence_engine.py/human_review.py esperan GenerationValidationReport (.syntax_passed, FASE
  33), no el ValidationReport crudo de SandboxLoopResult (.level_1_passed) -- mismo nombre
  generico, dos tipos -- aclarado en docstrings. 414/414 tests (404+10). 41 de 60 fases
  cubiertas. Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE
  45-46)".
- **Plan "AI Change Proposal Engine", FASE 42-44 (2026-08-11):** usuario pidio "continua todas
  las fases... hasta darla por terminada". PatchProposal extendida (tests_to_add/tests_to_remove/
  documentation_to_update, defaults compatibles). test_awareness.py: DELETE sobre test sin
  declarar en tests_to_remove -> ERROR. documentation_awareness.py: compara docs conocidas por
  el grafo vs declaradas, informativo + defensa en profundidad (ningun .md se escribe directo).
  confidence_engine.py: compute_composite_confidence() combina factores reales opcionales
  (llm/target/syntax/architecture/contract), promedio simple, nunca fabricado. 404/404 tests
  (390+14). 39 de 60 fases cubiertas. Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md`
  seccion "Checkpoint (FASE 42-44)".
- **Plan "AI Change Proposal Engine", FASE 40-41 (2026-08-11):** `dependency_awareness.py`
  (FASE 40) detecta imports nuevos de una propuesta y bloquea si referencian `ai_engine` (regla
  real ya establecida -- servicio FastAPI en su propio Docker, nunca importable); deteccion de
  dependencias circulares NO implementada (sin operacion real en graph_sdk que la exponga, no se
  fabrica). `contract_awareness.py` (FASE 41) compara consumidores frontend/tests conocidos por
  el grafo contra lo que una propuesta cubre cuando el target afecta un contrato -- reporta
  cobertura completa/parcial, nunca bloquea solo (visible, no prohibido). Verificado con datos
  reales de EquipmentViewSet.check_availability (contrato real, 6 consumidores). 390/390 tests
  (379 + 11). 36 de las 60 fases del plan cubiertas. Detalle: `ai_editor/.AGENT/
  AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 40-41)".
- **Plan "AI Change Proposal Engine", FASE 38 "Cross-Stack Generation" (2026-08-11):** unica
  fase de este plan que TOCA UN GUARDRAIL DE SEGURIDAD YA CERRADO -- ejecutada solo tras
  confirmacion explicita del usuario en 2 pasos (un "si" ambiguo desambiguado con pregunta
  directa: "Si, relajar el guardrail"). Antes: `proposal_validator._check_scope_and_operation()`
  (FASE 29) solo permitia escritura sobre el step MODIFY, una propuesta jamas tocaba mas de 1
  archivo real. Relajado de forma ACOTADA: tambien permite REVIEW no-documentacion (contrato/
  frontend/backend que el grafo YA vinculo) y RUN (tests) -- documentacion (.md) sigue bloqueada
  (FASE 43 exige que quede propuesta). De paso corrigio un bug latente real preexistente desde
  FASE 29 (la condicion original eximia CUALQUIER DELETE del chequeo, nunca antes documentado).
  3 cambios encadenados necesarios: UNDECLARED_CONTRACT_CHANGE de ERROR a WARNING,
  reconciliation.py filtra por severidad ERROR, build_source_context() extendido a los mismos
  steps ahora escribibles (sin esto el LLM no tendria old_content real para proponer cross-stack).
  Verificado end-to-end real: propuesta de 2 archivos (backend Django + frontend Vue) aplicada
  en un mismo sandbox, ambas APPLIED, checkout real intacto despues. 379/379 tests. Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 38)". 34 de 60 fases
  del plan cubiertas.
- **Plan "AI Change Proposal Engine", FASE 37 (2026-08-11):** `ai_editor/generation/
  architecture_compliance.py::check_architectural_compliance()` -- valida el codigo generado
  contra reglas YA documentadas y reales (CLAUDE.md/.AGENT.md, citadas en cada issue), regla del
  prompt maestro "no inventar reglas" cumplida literal: Selectors sin efectos secundarios,
  ViewSets sin ORM directo (warning), permisos importados correctamente, frontend sin axios
  directo. "tenant boundaries"/"shared components" quedan honestamente NOT_IMPLEMENTED (este
  proyecto no tiene concepto de tenant real). Heuristico por regex, no AST completo -- limitacion
  documentada. 376/376 tests (367 + 9). **Siguiente fase (FASE 38 "Cross-Stack Generation")
  requiere relajar un guardrail de seguridad ya cerrado (FASE 29: solo el step MODIFY principal
  puede recibir escrituras, nunca mas de 1 archivo real por propuesta hoy)** -- pendiente
  confirmacion explicita del usuario antes de tocarlo. Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 37)".
- **Plan "AI Change Proposal Engine", FASE 33-36 en batch (2026-08-11):** pedido explicito del
  usuario ("continua con fase 34 y demas, deja pruebas test para lo ultimo"). FASE 33
  (`validation_report.py`, consolida syntax/tests/contracts/errors/warnings), FASE 34
  (`reconciliation.py`, Graph Reconciliation version SCOPE -- el motivo #2 de POST-GRAPH 9 ya
  no aplica desde que `generation/` genera propuestas reales, el motivo #1 -- sandbox parcial --
  sigue vigente para reconstruccion COMPLETA del grafo), FASE 35 (`impact_recheck.py`, detecta
  drift del grafo desde que se planeo el cambio), FASE 36 (`code_quality.py`, corre `bandit`
  REAL -- unica herramienta de lint/quality declarada en pyproject.toml E instalada en el
  entorno, verificado antes de escribir codigo). **2 bugs reales encontrados y corregidos por
  mis propios smoke tests antes de declarar cada fase lista**: FASE 35 aproximaba mal el impacto
  predicho (subestimaba sistematicamente, producia BLOCK falso siempre) -- corregido con un
  baseline capturado via llamada real a calculate_impact(); FASE 36 reportaba PASS cuando NINGUN
  linter real habia corrido -- corregido para exigir al menos un check real ejecutado. Tests
  formales escritos al final del batch (21 nuevos), no fase por fase. 367/367 tests (346 + 21).
  Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 33-36,
  batch)". 33 de las 60 fases del plan cubiertas. Siguiente: sin decision tomada.
- **Plan "AI Change Proposal Engine", cadena de promocion (2026-08-11):** `ai_editor/
  generation/promotion.py::review_and_promote()` -- une FASE 32 (Sandbox Generation Loop) con
  approval.build_change_summary/record_decision (POST-GRAPH 11) y repository.
  promote_to_workspace (POST-GRAPH 12/20) en un solo flujo, pedido explicito del usuario
  ("continua con encadenar generation"). decision/confirm son parametros OBLIGATORIOS (nunca
  defaulteados a un valor que permita promover solo) -- cumple literal la regla final de
  seguridad del prompt maestro ("nunca LLM -> WRITE -> PRODUCTION"). Probado UNICAMENTE contra
  fake_workspace (tmp_path, mismo patron que test_ai_editor_commit_control.py) -- nunca
  invocado contra WORKSPACE_ROOT real. 346/346 tests (338 + 8 nuevos). El pipeline completo
  generation -> approval -> promote queda armado a nivel de mecanismo; probarlo contra el repo
  real (como se hizo en POST-GRAPH 21) requeriria la misma confirmacion explicita fresca del
  usuario, no es automatico. Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion
  "Checkpoint (Cadena de promocion)".
- **Plan "AI Change Proposal Engine", FASE 32 (2026-08-11):** `ai_editor/generation/
  sandbox_loop.py::run_sandbox_validation_loop()` -- flujo literal del prompt maestro
  PatchProposal -> Sandbox -> Apply -> Syntax Validation -> Tests, encadena create_sandbox
  (POST-GRAPH 7) + apply_proposal_to_sandbox (FASE 31) + run_validation (POST-GRAPH 8) +
  build_test_validation_report (POST-GRAPH 10), cero logica nueva. Verificado con 3 escenarios
  reales: propuesta valida -> ready_for_approval=True; sintaxis rota -> se aplica pero
  run_validation la atrapa (mismo patron real de POST-GRAPH 21); pre-validacion fallida -> nunca
  llega a validar sintaxis. WORKSPACE_ROOT intacto en los 3 casos. 338/338 tests (333 + 5
  nuevos). Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint
  (FASE 32)". Siguiente: sin decision tomada (FASE 33 o encadenar con approval/promote).
- **Plan "AI Change Proposal Engine", FASE 31 (2026-08-11):** `ai_editor/generation/
  patch_integration.py::apply_proposal_to_sandbox()` -- primera pieza de `generation/` que
  ESCRIBE algo, pero solo dentro de un Sandbox real ya creado por el caller (POST-GRAPH 7),
  nunca sobre `WORKSPACE_ROOT`, nunca llama a `promote_to_workspace()`. Convierte una
  `PatchProposal` validada (FASE 29) en operaciones reales del Patch Engine y las aplica via
  `apply_operation()` (POST-GRAPH 6) -- doble re-validacion, nunca confia ciegamente en el LLM.
  **Bug real encontrado y corregido dentro de esta misma fase**: el fingerprint "esperado" se
  calculaba releyendo el sandbox en el momento de convertir cada operacion (coincide consigo
  mismo trivialmente, anula la deteccion de drift entre operaciones) -- corregido usando el
  fingerprint del `old_content` ya verificado contra el repo real por FASE 29. Verificado
  end-to-end: MODIFY se aplica sobre el sandbox, el archivo REAL queda byte-a-byte identico;
  guardrail de `apply_operation()` sigue rechazando un intento de escribir sobre
  `WORKSPACE_ROOT` aunque la pre-validacion pasara. 333/333 tests (327 + 6 nuevos). Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 31)". Siguiente:
  sin decision tomada (FASE 32/33 o encadenar generation/ con validation/approval/repository
  ya existentes).
- **Plan "AI Change Proposal Engine", FASE 30 (2026-08-11):** `ai_editor/generation/retry.py::
  generate_with_retry()` -- orquesta generator (FASE 28) + proposal_validator (FASE 29) en
  hasta 3 intentos (`DEFAULT_MAX_RETRIES`, literal del prompt maestro). Cada intento fallido
  genera una nota de correccion (codigo+mensaje+campo de cada issue ERROR real) que se reenvia
  al LLM en el prompt siguiente via `PREVIOUS_ATTEMPTS_FEEDBACK` (`prompts.build_prompt()`
  extendido). `RetryOutcome` conserva el historial completo, no solo el resultado final.
  Probado end-to-end: intento 1 FAIL, intento 2 FAIL (mismo error), intento 3 PASS -- exacto al
  ejemplo del prompt maestro, y verificado que la correccion real llega al prompt del intento
  siguiente (no solo que se calcula). 327/327 tests (320 + 7 nuevos). Detalle:
  `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` seccion "Checkpoint (FASE 30)". Usuario eligio
  FASE 30 sobre FASE 31 via pregunta de desambiguacion (un "si" ambiguo a "FASE 30 o FASE 31?").
  Siguiente: FASE 31 "Patch Engine Integration" (empieza a conectar generation/ con
  patch/repository reales).
- **Plan "AI Change Proposal Engine", FASE 29 (2026-08-11):** `ai_editor/generation/
  proposal_validator.py::validate_proposal_against_repo()` -- valida una `PatchProposal` YA
  CONSTRUIDA (FASE 25/28) contra el estado REAL del repo/plan (no solo forma, como FASE 28):
  archivo existe, old_content/hash coinciden con el contenido real, scope dentro del
  ChangePlan, sin contratos no declarados/archivos sensibles/limites superados. Reusa
  `patch.fingerprint` y `repository.sandbox._SENSITIVE_PATTERNS` en vez de reimplementar.
  "Dependencias inesperadas" queda documentado como NO implementado (requiere FASE 40).
  320/320 tests (308 + 12 nuevos). Detalle: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md`
  seccion "Checkpoint (FASE 29)" y `AI_EDITOR_BASELINE.md` seccion 29. Siguiente: decidir entre
  FASE 30 (Retry Engine) o FASE 31 (Patch Engine Integration).
- **Plan "AI Change Proposal Engine", FASE 24-28 -- primera ejecucion (2026-08-11):** nuevo
  plan de 60 fases pegado por el usuario tras el cierre de POST-GRAPH 0-23, arranca con
  `ai_editor/generation/` (11mo submodulo): LLM + contexto MINIMO real (nunca el grafo
  completo) -> `PatchProposal` estructurada, sin aplicar todavia. **Bug real encontrado en el
  paso 0 obligatorio del prompt ("ejecutar tests actuales, registrar baseline")**: la suite
  daba 256/257 al correrla de nuevo, no 257/257 como documentaba la sesion anterior -- los
  nodos `Documentation` del grafo guardan su path relativo al repo GIT completo, no a
  `WORKSPACE_ROOT`, bloqueando cualquier plan que referenciara documentacion fuera de
  `ecommerce_sintel/` (ej. `IMPLEMENTATION_SUMMARY.md`, que vive un nivel arriba). Corregido
  sin tocar `project_knowledge_graph` (`ai_editor/workspace.py::REPO_ROOT`/
  `resolve_repo_doc_path()`, `planner/validator.py` degrada a warning). Baseline real: 263/263.
  FASE 25 (modelos: ChangeGenerationRequest/PatchProposal/PatchOperation/GenerationResult/
  GenerationIssue/GenerationConfidence) + FASE 26 (Source Context Builder, lee solo rango+
  margen de codigo real, nunca el archivo completo) + FASE 27 (prompt engine con 8
  estrategias segun tipo de cambio) + FASE 28 (salida LLM estructurada -- texto libre siempre
  REJECT, nunca reparado en silencio, verificado por test). 308/308 tests (263 + 45 nuevos).
  Nunca se corrio contra un LLM real (no disponible en este entorno) -- mockeado en tests, con
  contexto real de punta a punta. Detalle completo: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_
  ENGINE.md` y `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 29. Siguiente: FASE 29 "Patch
  Proposal Validator" (validar CONTRA el repo real antes de conectar con el Patch Engine).
- **POST-GRAPH 21 del plan "AI Editor Runtime" (2026-08-11): CONFIRMADO REAL contra el
  repositorio real.** Bloqueo del clasificador de auto mode impidio que esta sesion ejecutara
  la escritura directamente -- se preparo un script autocontenido (`post_graph_21_real_e2e_demo.py`)
  y se delego la ejecucion al usuario, quien lo corrio dos veces. **Primer intento**: bug real (mio,
  no del pipeline) en el offset de insercion de un ADD -- el guardrail de POST-GRAPH 20
  (`promote_to_workspace(..., validation_report=...)`) lo bloqueo correctamente
  (`VALIDATION_FAILED`, 0 archivos escritos) -- primera vez que ese guardrail se prueba contra un
  error real, no un test. **Segundo intento (corregido)**: pipeline completo end-to-end sobre
  `HomeCardGroupSelector.get_by_name` (`core/services/commands.py`) -- `PROMOTE -> PROMOTED`
  (archivo real verificado modificado), `ROLLBACK -> ROLLED_BACK` (archivo real verificado
  identico al original). Verificado independientemente por esta sesion via `git diff` (0 residuo).
  Script temporal borrado despues de usarlo. Detalle completo:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 26.
- **POST-GRAPH 20 del plan "AI Editor Runtime" (2026-08-11):** auditoria de los 5 invariantes
  criticos del prompt maestro. **Gap real de seguridad encontrado**: `promote_to_workspace()` no
  verificaba que la validacion de sintaxis hubiera pasado antes de escribir sobre el workspace
  real -- dependia enteramente de que el humano no aprobara un cambio con sintaxis rota, sin
  ningun guardrail de codigo. Corregido: parametro opcional `validation_report`, rechaza
  estructuralmente (`VALIDATION_FAILED`) si `level_1_passed=False`, sin importar la aprobacion.
  Retrocompatible. 257/257 tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 25.
  **POST-GRAPH 21-23 piden ejecutar una modificacion sobre el REPOSITORIO REAL** -- primera vez
  que el plan cruza esa linea explicitamente; NO se hara sin confirmacion separada del usuario.
- **POST-GRAPH 19 del plan "AI Editor Runtime" (2026-08-11):** creados los 7 documentos que pide
  el prompt maestro en `ai_editor/.AGENT/` (ARQUITECTURA/CHANGE_FLOW/SECURITY_MODEL/PATCH_ENGINE/
  VALIDATION_MODEL/GRAPH_CLIENT/OPERATIONS_GUIDE). El ejemplo completo de OPERATIONS_GUIDE.md se
  corrio linea por linea contra el caso Renting real para confirmar que no tiene ejemplos rotos.
  0 codigo nuevo, 251/251 tests sin cambios. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md`
  seccion 24.
- **POST-GRAPH 18 del plan "AI Editor Runtime" (2026-08-11):** auditoria real de seguridad contra
  la lista del prompt maestro -- la mayoria ya estaba cubierta (path traversal, secret exposure,
  command injection). **Symlinks: se penso que era un gap, VERIFICADO REAL que NO lo es**
  (`.resolve()` ya sigue symlinks antes del chequeo de boundary, probado con un symlink real).
  **3 gaps reales encontrados y corregidos**: sin limite de tamano de patch (`MAX_PATCH_CONTENT_
  BYTES=5MB`), sin limite de cantidad de archivos en sandbox (`MAX_SANDBOX_FILES=500`), lista de
  patrones sensibles incompleta (faltaban certificados/backups/dumps que el prompt pide
  explicito). 251/251 tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 23.
- **POST-GRAPH 17 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/audit/metrics.py::
  compute_metrics()` agrega metricas reales sobre los registros de `audit_pipeline_run()` --
  `graph_mismatches`/`unexpected_impacts`/tiempos por etapa quedan `None` explicito (nunca `0`,
  para no fingir "sin problemas" cuando en realidad nunca se midio). Verificado real: pipeline
  completo con patch+rollback, metricas correctas sobre datos reales. 237/237 tests. Detalle:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 22.
- **POST-GRAPH 15-16 del plan "AI Editor Runtime" (2026-08-11):** POST-GRAPH 15 (multi-step/DAG
  multi-modulo) documentado como DIFERIDO -- requeriria extender el planner de topologia estrella
  a grafo de dependencias real entre multiples targets, sin caso real que lo motive. POST-GRAPH 16
  (Rollback): `PromoteResult` ahora captura `files_before` (contenido completo antes de
  sobrescribir), `rollback_promotion()` restaura exacto -- no depende de git. Verificado real:
  ciclo promote->rollback sobre el caso Renting, contenido final identico al original. 230/230
  tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` secciones 20-21.
- **POST-GRAPH 14 del plan "AI Editor Runtime" (2026-08-11):** actualizado
  `ai_editor/.AGENT/AUTONOMOUS_CHANGE_LOOP.md` con el diagrama real de 12 pasos (los 10
  submodulos ya tienen logica real) -- sin codigo de orquestacion nuevo, la decision de Fase 17
  de no automatizar el loop completo sigue vigente sin cambios (mas superficie real que orquestar
  ahora, no una razon para relajar la regla).
- **POST-GRAPH 13 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/audit/` -- registro
  append-only propio (`CHANGE_AUDIT_LOG.jsonl`, no reusa `project_knowledge_graph.audit.query_log`
  que es "internal"). **Bug real encontrado y corregido en la propia verificacion**: la sanitizacion
  de secretos (`api_key`/`password`/`token`/etc.) solo funcionaba en campos ANIDADOS, no en los de
  primer nivel -- `log_change_operation(api_key="sk-...")` se colaba integro al log en texto plano
  hasta que se corrigio (una sola llamada `_sanitize(fields)` sobre el dict completo en vez de un
  dict-comprehension manual). Verificado antes/despues del fix con una escritura real a disco.
  224/224 tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 19.
- **POST-GRAPH 12 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/repository/promote.py`
  -- primera pieza cuyo proposito es escribir sobre un checkout real. 4 guardrails
  independientes probados uno por uno (sin aprobacion, aprobacion rechazada, aprobado sin
  confirmar, drift del workspace real detectado y aborta todo-o-nada) -- **cero invocaciones
  contra `WORKSPACE_ROOT` real en toda la sesion**, solo contra `tmp_path`/repos git temporales,
  tal como se comprometio antes de empezar la fase. `commit_changes()` hace `git add`+`git
  commit` local, nunca push (verificado: sin remoto configurado). 215/215 tests. Detalle:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 18.
- **POST-GRAPH 11 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/approval/` (submodulo
  nuevo) -- `build_change_summary()` compone el CHANGE SUMMARY completo para revision humana
  (cero consultas nuevas al grafo, agrega datos ya reales de fases previas);
  `record_decision(APPROVE|REJECT|MODIFY_PLAN|REQUEST_EXPLANATION)` valida y registra. Siempre
  aclara que Graph Reconciliation no esta verificado (honestidad sobre el gap de POST-GRAPH 9).
  Pipeline completo verificado real: intent->resolver->planner->sandbox->validation->approval
  encadenados sobre el caso Renting. 207/207 tests. Detalle:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 17. **Siguiente fase (POST-GRAPH 12, Commit
  Control) es la primera que puede escribir sobre el checkout REAL** -- se construira el
  mecanismo gateado por aprobacion+fingerprint, pero NO se invocara contra el WORKSPACE_ROOT real
  sin pedir confirmacion explicita separada al usuario en el momento.
- **Decision del usuario sobre el fork del sandbox (2026-08-11):** ante la pregunta de como
  resolver que el sandbox parcial bloquea tests reales/reconciliacion de grafo, el usuario eligio
  explicitamente **"seguir parcial, avanzar el resto del pipeline"** (no construir sandbox
  completo con Docker por ahora) -- Referencia para futuras sesiones: no asumir que hay que
  construir Docker/sandbox completo, seguir documentando gaps como `NOT_IMPLEMENTED` explicito
  donde corresponda y avanzar lo demas.
- **POST-GRAPH 9-10 del plan "AI Editor Runtime" (2026-08-11):** Reconciliation (9) queda
  `NOT_IMPLEMENTED` por 2 motivos reales (sandbox parcial + no hay generacion de codigo real que
  produzca sorpresas todavia). Test Impact Execution (10) es parcialmente real:
  `build_test_validation_report()` clasifica tests required/recommended con datos YA existentes
  del grafo, nunca los ejecuta (`tests_run=False` siempre). 196/196 tests. Detalle:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 16.
- **POST-GRAPH 8 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/validation/` -- SOLO
  Nivel 1 (sintaxis) de 5 implementado y real (`ast.parse` para Python, `node --check` para
  JS/Vue). **Estado honesto: PARTIAL, no PASS completo** -- Niveles 2-5 (tests reales/contratos/
  grafo antes-despues/impacto) requieren un sandbox de tipo distinto (copia completa del repo o
  git worktree, mas Docker) que el sandbox parcial actual (POST-GRAPH 7) no provee; queda
  `NOT_IMPLEMENTED` explicito, no fabricado. Verificado real: sandbox limpio del caso Renting
  pasa 8/8; sintaxis Python realmente rota inyectada via `apply_operation()` se detecta
  correctamente. **Con esta fase los 8 submodulos de `ai_editor/` tienen logica real por primera
  vez** (varios con alcance deliberadamente acotado). 190/190 tests. Detalle:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 15.
- **POST-GRAPH 7 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/repository/sandbox.py`
  -- `create_sandbox(plan)` copia solo los archivos reales que un plan toca a un directorio
  temporal aislado; salta paths sensibles (.env/secrets/keys). **Verificado end-to-end real**: el
  ciclo completo REQUEST->RESOLVE->PLAN->SANDBOX->PATCH sobre `EquipmentViewSet.
  check_availability` confirma que el archivo REAL del repo queda byte-a-byte identico
  antes/despues de aplicar un patch sobre el sandbox -- el checkout real nunca se toca. 178/178
  tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 14.
- **POST-GRAPH 6 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/patch/` -- MECANISMO de
  aplicar cambios de forma segura (`apply_operation`: verifica fingerprint sha256 del contenido
  real antes de escribir, aborta si no coincide). **NO genera codigo real** -- eso requeriria una
  capa de generacion (LLM escribiendo diffs sobre Django/Vue real) que ninguna fase construye
  todavia; alcance deliberadamente acotado, documentado explicito. Guardrail estructural: rechaza
  escribir sobre `WORKSPACE_ROOT` (checkout real) salvo flag explicito, y rechaza path traversal.
  12 tests nuevos, TODOS contra `tmp_path` -- 0 escrituras contra el repo real durante toda la
  verificacion. 170/170 tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 13.
- **POST-GRAPH 5 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/workspace.py` (nuevo,
  compartido) + `ai_editor/planner/validator.py::validate_plan()` -- primera pieza de `ai_editor`
  que LEE el filesystem real (nunca escribe). **Bug real encontrado y corregido**: los paths de
  nodos frontend en el grafo son relativos a `frontend/src/`, no a la raiz del proyecto -- la
  primera version reportaba TODOS los consumidores frontend reales como "no existen en disco".
  Corregido probando ambas raices contra el disco (`resolve_repo_file()`) en vez de una
  heuristica fragil de tipo de nodo. Verificado: el plan real completo de
  `EquipmentViewSet.check_availability` (backend+frontend) queda `APPROVED` tras el fix.
  158/158 tests. Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 12. **POST-GRAPH 6
  (Patch Engine) es la primera fase que introduce el CONCEPTO de escritura -- el mecanismo se
  construye como logica pura probada solo contra `tmp_path`, ningun archivo real de
  `ecommerce_sintel/` se toca hasta que el sandbox de POST-GRAPH 7 exista.**
- **POST-GRAPH 4 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/planner/` deja de ser
  scaffold -- `build_change_plan(context)` convierte el `ChangeContext` (POST-GRAPH 3) en pasos
  concretos (file/symbol/lineas/operation/reason/dependencies/risk/validation), 0 llamadas
  nuevas al grafo (solo reordena lo que resolver ya trajo). Target siempre step 1
  (`MODIFY`), dependientes en `REVIEW`, tests en `RUN`. Verificado real: 18 pasos sobre
  `EquipmentViewSet.check_availability` con lineas exactas del archivo real. 146/146 tests.
  Detalle: `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 11. **Siguiente fase (POST-GRAPH 5,
  Plan Validator) es la ULTIMA antes del Patch Engine** -- POST-GRAPH 6 introduce ESCRITURA real
  sobre el repo, requiere mas cuidado/posible confirmacion explicita del usuario antes de avanzar.
- **POST-GRAPH 3 del plan "AI Editor Runtime" (2026-08-11):** `ai_editor/resolver/` deja de ser
  scaffold -- `resolve_change_context(intent)` resuelve cada entidad del `ChangeIntent` contra
  `graph_client.find_node()` y compone `resolve_change()`/`build_context_packet()` (ya reales)
  para el resultado final. **Bug real encontrado y corregido en la misma pasada**: `find_node()`
  no distingue match exacto de match fuzzy -- probado con `"Equipment"` (Renting tiene 0 Models
  reales): devolvia `FeaturedEquipmentCardSerializer` por matcheo de substring, que el resolver
  iba a tratar como confirmado. Corregido SIN TOCAR `project_knowledge_graph` (fases cerradas) --
  el resolver mismo exige `node["name"] == nombre_pedido`, si no hay coincidencia exacta la
  entidad va a `unresolved_entities` con nota explicita. Verificado real: el caso completo
  (`EquipmentViewSet.check_availability` + `Equipment`) contra el grafo real produce
  `PARTIALLY_RESOLVED` honesto, no un `RESOLVED` fabricado. 139/139 tests. Detalle:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 10.
- **POST-GRAPH 2 del plan "AI Editor Runtime" (2026-08-11):** decision directa del usuario --
  `ai_editor` accede a un LLM totalmente independiente (sin importar `ai_engine.llm_factory`),
  via `ai_editor/llm/` NUEVO (3 proveedores intercambiables Ollama/OpenAI/Anthropic sobre
  `urllib.request` stdlib puro, 0 dependencias nuevas, seleccionable por
  `AI_EDITOR_LLM_PROVIDER` o por argumento por-llamada). `ai_editor/intent/` deja de ser
  scaffold: `interpret_request()` interpreta la solicitud humana via el LLM Y cruza el `domain`
  propuesto contra `graph_client.find_node()` (grafo real) -- si el LLM alucina una app
  inexistente, el resultado queda `NEEDS_CLARIFICATION`, nunca se confia ciegamente. Verificado
  real: `domain="renting"` (real) -> RESOLVED; `domain` inventado -> NEEDS_CLARIFICATION con la
  ambiguedad explicita. 133/133 tests. Detalle completo:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 9.
- **POST-GRAPH 0-1 del nuevo plan "AI Editor Runtime" (2026-08-11):** con el Site Knowledge Graph
  cerrado, arranco un plan separado (POST-GRAPH 0-23) para construir `ai_editor/` de scaffold a
  sistema real de planificacion/patch/validacion de cambios. POST-GRAPH 0: auditoria de
  `ai_editor/` (6 de 7 submodulos siguen siendo scaffold puro, solo `graph_client/` tiene logica)
  y `graph_sdk/` (13 operaciones) -- 3 gaps reales encontrados (el prompt pide `find_node`/
  `get_app_summary`/`get_graph_status`, ninguna existia en `graph_sdk`, pero las 3 tienen logica
  YA EXISTENTE reusable 1:1). POST-GRAPH 1: cerradas las 3 con re-exportaciones puras (0 logica
  nueva) -- `find_node` usa deliberadamente `resolve_change_target` (exacto-antes-que-fuzzy) y NO
  `find_node_context` (que tiene un bug de matching conocido y sin resolver desde antes de esta
  sesion). `graph_client` ahora expone 16 operaciones, documentado como "LA FRONTERA OFICIAL"
  entre `ai_editor` y `project_knowledge_graph`. Verificado real: `resolve_change()` y
  `build_context_packet()` corridos DESDE `ai_editor.graph_client` contra el grafo real (9575
  nodos) sin tocar JSON internos. 122/122 tests. Detalle completo:
  `ai_editor/.AGENT/AI_EDITOR_BASELINE.md`.
- **CIERRE del rediseno "Site Knowledge Graph / AI Editor Runtime" (2026-08-11):** las 22 fases
  (FASE 0-21) estan completas -- reporte ejecutivo de cierre en
  `project_knowledge_graph/.AGENT/SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md` (que se construyo, las 2
  decisiones de alcance deliberadas sobre autonomia de codigo -- Fases 14/17, no implementadas a
  proposito por seguridad --, estado final verificado: 9575 nodos/20335 aristas, 120/120 tests,
  4 limitaciones conocidas sin resolver documentadas).
- **FASE 21 "Validacion Global" (2026-08-10):** pasada final end-to-end del rediseno "Site
  Knowledge Graph" completo -- `cli audit` (full rebuild real, 9575 nodos/20335 aristas, sin
  drift respecto a lo documentado), `validate`/`viz`/`snapshots`/`validation-report`/`query-log`
  corridos contra el grafo recien reconstruido, y la suite pytest completa (120/120) corrida dos
  veces sin diferencia. 0 regresiones en las 18 fases de codigo (Fases 1-18). Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 20 "Limpieza Documental" (2026-08-10):** busqueda en TODO el repo de referencias a los
  9 archivos de `ai_engine` retirados en la extraccion 2026-08-09
  (`project_map.py`/`knowledge_graph.py`/`dependency_graph.py`/`auditor.py`/etc.) y a
  `GraphImpactAnalysisTool` (Fase 0). Codigo Python: 0 bugs reales (todos los matches eran
  comentarios historicos correctos). **4 docs en `ai_engine/.AGENT/` (la referencia VIVA que
  CLAUDE.md manda leer) tenian referencias ACTUAL-PERO-INCORRECTAS, corregidas**:
  `FLIJO_COMPLETO_IA_ENGINE.md` (arbol de archivos + comandos `python ai_engine/auditor.py` que
  ya fallarian + descripcion desactualizada de `node_analyze_impact`), `GUIA_USO.md` (seccion
  completa del auditor retirado), `AI_SUPPORT_SCOPE.md` (excepcion `graph_tools.py` presentada
  como vigente cuando esta cerrada), `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md` (tabla de
  clasificacion de 2026-08-08 con 9 archivos ya borrados marcados como si solo estuvieran
  "separados conceptualmente"). Todo corregido con banners de retiro + puntero al estado actual,
  sin borrar el contenido historico. 0 codigo nuevo, 120/120 tests siguen pasando. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 19 "Documentacion" (consolidacion) en project_knowledge_graph (2026-08-10):**
  auditoria de `ARQUITECTURA_COMPLETA_GRAFO.md` secciones 2/4/7 contra el codigo real -- 5
  defectos de documentacion reales encontrados y corregidos: lista de funciones de scanners
  desactualizada (Fase 3-7), `query.py` listado con solo 2 de 18 funciones reales, afirmacion
  falsa de "pytest no instalado en el host" (verificado: SI corre, 120/120), referencia a
  `GraphImpactAnalysisTool` (borrado en Fase 0), y afirmacion falsa de que `data/` esta
  gitignored (esta untracked pero NO por `.gitignore`). 0 codigo nuevo. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 18 "Observability" en project_knowledge_graph (2026-08-10):** `audit/query_log.py`
  agrega logging real de auditoria (append-only JSONL) a las 13 funciones de `graph_sdk` --
  operacion/args/duracion/`graph_snapshot`/resumen del resultado, NUNCA `meta` completo de un
  nodo (verificado: `EnvVar` ya solo guarda nombres, no valores, pero se poda `meta` de TODO tipo
  de nodo igual, por seguridad). Best-effort: un fallo de escritura no rompe la consulta real. CLI:
  `project-graph query-log`. 120/120 tests. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 17 "Autonomous Change Loop" (2026-08-10):** SOLO documentacion
  (`ai_editor/.AGENT/AUTONOMOUS_CHANGE_LOOP.md`), mismo criterio de seguridad que Fase 14 --
  orquestar un loop automatico alrededor de `patch/` (deliberadamente no implementado, blast
  radius de modificar codigo sin supervision) no aporta nada real ni es una decision que se tome
  implicitamente. Documenta el diseno completo y marca el "HUMAN GATE" obligatorio antes de
  aplicar cualquier patch. 0 codigo nuevo. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 16 "Change Validation" en project_knowledge_graph (2026-08-10):**
  `audit/change_validation.py::build_change_validation_report()` compone Fase 15
  (`detect_changed_symbols`, evidencia real del git diff actual) + Fase 10
  (`calculate_change_impact` por simbolo, agregado) + el validator ya existente
  (`run_all_validations`, 6 chequeos) en el "CHANGE VALIDATION REPORT" del plan:
  files/symbols/contracts/frontend/backend afectados, tests requeridos, consistencia de
  grafo/contratos, riesgo agregado. **Decision de alcance:** `tests_required` se CALCULA
  pero NO se ejecuta automaticamente (muchos tests reales requieren Postgres/Redis/Docker no
  disponibles desde el host bare) -- reporta `tests_run: false` en vez de fabricar un
  pass/fail. Verificado contra el repo real: 16 contratos / 59 frontend / 31 backend / 38
  tests afectados por el diff actual (~200 simbolos), `risk: HIGH`; `contract_consistency`
  detecto correctamente 8 endpoints reales sin `SERIALIZES` (gap preexistente del enricher de
  contrato, Fase 4, no introducido ni corregido aqui -- este modulo REPORTA, no arregla). CLI:
  `project-graph validation-report` (exit 1 si risk==HIGH). 114/114 tests. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 15 "Incremental Semantic Graph" en project_knowledge_graph (2026-08-10):** agrega
  `detect_changed_symbols()` (git diff -U0 -> hunks -> Symbol nodes reales tocados por rango de
  linea) -- el nivel "changed symbols" que faltaba (antes solo "changed apps"). **Bug real
  encontrado y corregido**: `subprocess.run(text=True)` sin `encoding='utf-8'` usaba cp1252 en
  Windows y crasheaba contra el diff real (comentarios/strings en español con acentos) --
  corregido con `encoding="utf-8", errors="replace"`. Verificado: un hunk sintetico en
  renting/api/views.py identifica exacto `EquipmentViewSet.check_availability`. Limitacion
  documentada: el REBUILD del grafo sigue siendo completo, esto solo mejora la DETECCION.
  108/108 tests. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 14 "AI Editor Runtime" -- `ecommerce_sintel/ai_editor/` (2026-08-10):** SCAFFOLD
  deliberado, no funcional. 7 submodulos del plan (intent/resolver/planner/repository/patch/
  validation/graph_client). Decision de alcance explicita: `patch/` (modificar codigo
  autonomamente) requiere decision humana separada dado el blast radius -- solo `graph_client/`
  tiene codigo real (wrapper de solo lectura sobre graph_sdk), los otros 6 son puros docstrings
  de arquitectura sin logica ejecutable (verificado por AST). Mantiene la frontera de Fase 0:
  ai_editor no importa ai_engine. 102/102 tests. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 13 "Graph SDK" en project_knowledge_graph (2026-08-10):** nuevo paquete
  `project_knowledge_graph/graph_sdk/` -- capa estable con las 11 operaciones del plan
  (resolve_change/find_symbol/find_file/find_endpoint/find_consumers/trace_data_flow/
  trace_execution/find_tests/find_docs/calculate_impact/build_change_plan), todas
  re-exportaciones de funciones ya construidas en Fases 5-12 (solo 4 primitivos nuevos:
  find_symbol/find_file/find_endpoint/find_consumers). Devuelve dicts planos, oculta
  Node/KnowledgeGraph internals. 97/97 tests. Detalle en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 12 "Graph Context Packet" en project_knowledge_graph (2026-08-10):**
  `build_graph_context_packet(request)` comprime `resolve_change()` a solo id/type/name/file/
  lineas (nunca meta completo) + stats total_graph_nodes vs relevant_nodes. Verificado real:
  9575 nodos totales -> 20 relevantes para `EquipmentViewSet.check_availability`. 96/96 tests.
  Detalle en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 11 "Change Resolver" en project_knowledge_graph (2026-08-10):** `resolve_change(request)`
  compone Fases 5/6/10 en el envelope completo del plan (intent/target/primary_files/symbols/
  contracts/frontend_consumers/backend_dependencies/data_flows/execution_paths/tests/docs/config/
  risk/change_order/validation_plan). Sin parsing NLP (mismo alcance de Fase 10). 95/95 tests.
  Detalle en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 10 "Change Graph" en project_knowledge_graph (2026-08-10, "la fase critica" del plan
  original):** `calculate_change_impact(target)` compone las consultas de Fases 5-9 en impacto
  categorizado directo/indirecto (frontend/backend/contract/test/doc/config) + risk (heuristico
  por conteo, no ML) + orden recomendado (plantilla estatica marcada como tal). Deliberadamente
  NO se implemento parsing de lenguaje natural (`ChangeIntent`, ej. "Agregar alquiler por horas"
  -> JSON) -- eso requiere un LLM real, es trabajo de la futura Fase 14 "AI Editor Runtime", no
  de este modulo estatico. **Bug real encontrado y corregido:** los primitivos genericos
  `transitive_dependents()` no distinguian aristas ESTRUCTURALES (`CONTAINS`/`BELONGS_TO`) de
  FUNCIONALES -- cambiar un metodo de ViewSet mostraba su propia clase como "impacto directo"
  (una clase siempre "contiene" su metodo, eso no es impacto real), inflando el conteo de 42 a
  797. Corregido con una funcion nueva que excluye ambas (sin tocar la funcion generica
  pre-existente, usada por otros consumidores). Verificado contra Renting/Availability: impacto
  de `check_availability` incluye correctamente `availabilityService.check` y
  `ARQUITECTURA_COMPLETA_RENTIG`. 94/94 tests. Sin cambios de nodos/aristas (capa de consulta
  pura). Detalle completo en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 9 "Configuration/Infrastructure Graph" en project_knowledge_graph (2026-08-10):** agrega
  `Port`/`NginxRoute` (node types) + `EXPOSES`/`PROVIDES`/`ROUTES_TO` (aristas) +
  `find_configuration_for(query)`. Nuevo enricher `enrichers/nginx.py`. **2 bugs reales
  encontrados y corregidos:** (1) `.env.production.example` vive dentro de `ecommerce_sintel/`,
  no en la raiz del repo -- `PROVIDES` quedaba en 0 aristas en todo el grafo hasta el fix. (2) el
  regex de `location` matcheaba como substring de `geolocation=()` (header Permissions-Policy
  real), extendiendo la captura cientos de lineas -- corregido anclando a inicio de linea.
  Verificado contra docker-compose.yml/nginx-common.conf reales: 8 Port reales, django PROVIDES
  55 EnvVar reales, `nginx:/` -> django (correcto), `/api/v1/internal/` sin ruta (bloqueado,
  correcto). Grafo: 9561/20106 -> 9575/20335. 93/93 tests. Detalle completo en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 8 "Documentation Graph" en project_knowledge_graph (2026-08-10, prompt maestro de 22
  fases -- FASE 8 completada; desde aqui el usuario autorizo continuar TODAS las fases restantes
  (9-21) sin pausar por confirmacion, manteniendo el mismo rigor de evidencia real +
  checkpoint):** agrega `REFERENCES` (`Documentation -> File/Symbol/Endpoint`, via rutas/
  `Clase.metodo`/URLs citadas entre backticks en la prosa real de cada doc) y
  `find_docs_for_change(query)`, verificado con el ejemplo textual EXACTO del plan
  ("renting availability" -> `ARQUITECTURA_COMPLETA_RENTIG.md` como resultado #1). Grafo:
  9561/18790 -> 9561/20106 (+1316 aristas, sin nodos nuevos). 85/85 tests. Detalle completo en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 7 "Test Graph" en project_knowledge_graph (2026-08-10, prompt maestro de 22 fases --
  solo FASE 7 ejecutada, checkpoint PASS, sin avanzar a FASE 8):** sin node types nuevos (Test/
  TestSuite/E2ETest) -- un metodo de test YA es un `Symbol` real, solo se marca `meta.is_test`
  (clase `*TestCase`/`APITestCase`, o funcion `test_*` estilo pytest). Agrega `VALIDATES`
  (`Test-Symbol -> Endpoint` via `self.client.verbo(url)` real, soporta f-strings) y `TESTS`
  (`Test-Symbol -> Symbol` via llamada directa `ClaseX.metodo(...)` dentro del test) mas la
  consulta obligatoria `find_tests_for_change(target)` ("que tests ejecutar si cambio esto").
  **Bug real encontrado y corregido durante la verificacion:** `find_by_name('Product')`
  devuelve 460 matches por substring en orden no determinista -- el primer resultado
  Symbol/Endpoint/Model NUNCA era el Model `Product` real. Corregido priorizando coincidencia
  EXACTA de nombre. Verificado contra shop/tests.py (VALIDATES real a `/api/v1/shop/products/`)
  y renting/tests_endpoints.py (TESTS real a `RentalRequestCommands.create_request`), muestreo de
  16 aristas sin falsos positivos. Grafo: 9561/18265 -> 9561/18790 (+525 aristas, sin nodos
  nuevos). 857 Symbol marcados is_test. 78/78 tests. Alcance: solo tests Python (Django
  TestCase/APITestCase + pytest) -- Vitest/.test.js y Playwright E2E quedan PLANIFICADOS, no
  implementados (sintaxis de bloque distinta, requiere extractor nuevo). Detalle completo en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 6 "Execution Graph" en project_knowledge_graph (2026-08-10, prompt maestro de 22 fases
  -- solo FASE 6 ejecutada, checkpoint PASS, sin avanzar a FASE 7):** agrega `TRIGGERS`
  (`Model -> Signal` via `sender=X` real de `@receiver(...)`) y `QUEUES` (`Symbol -> Task` via
  `.delay(...)`/`.apply_async(...)` real) mas la consulta obligatoria `trace_execution(start)`,
  que compone TODAS las aristas de Fases 0-6 en un ExecutionPath numerado (recorrido greedy +
  `also` con el resto de aristas no seguidas en cada paso). **Bug real PRE-EXISTENTE encontrado y
  corregido** (no introducido por esta fase): `is_task_function()` no reconocia
  `@shared_task(bind=True, ...)` (llamada directa, patron real dominante del proyecto) -- las 8
  tasks reales de `notifications/tasks.py` eran invisibles (0 nodos Task para toda esa app).
  Corregido: Task paso de 8 a 19 nodos. 2 correcciones de diseño en `trace_execution()`
  encontradas verificando contra casos reales: (1) desambiguacion de `IMPLEMENTED_BY` por URL
  real cuando un Endpoint fan-out a varias acciones de ViewSet (evita elegir la primera por
  casualidad de orden); (2) fallback `CALLS` a nivel de clase via `CONTAINS`, necesario porque
  este proyecto obliga Service Layer (ViewSets nunca tocan Model directo). Verificado contra
  `NotificationCommands.dispatch_notification` (encola 5 tasks reales, visibles gracias a `also`)
  y `availabilityService.check` (4 pasos reales hasta `EquipmentCommands`). Grafo: 9550/18217 ->
  9561/18265. 72/72 tests. Detalle completo en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 5 "Data Flow Graph" en project_knowledge_graph (2026-08-10, prompt maestro de 22 fases
  -- solo FASE 5 ejecutada, checkpoint PASS, sin avanzar a FASE 6):** agrega `READS_FROM`/
  `WRITES_TO` (`Symbol -> Model`, evidencia real AST del patron `Model.objects.verbo(...)`) y la
  consulta obligatoria `trace_data_flow(target)` (`Model` o `Model.campo`), que compone TODAS las
  aristas ya existentes de Fases 0-5 en un recorrido `database -> serializer -> API -> frontend
  -> component` legible -- sin node types nuevos, siguiendo la guia del propio plan ("la
  prioridad es crear relaciones de flujo"). **1 bug real encontrado y corregido durante la
  implementacion:** atribuir usos de modelo por nombre CRUDO de funcion mezclaba metodos
  homonimos de clases distintas en el mismo archivo (`shop/services/selectors.py` tiene tanto
  `ProductSelector.list_active()` como `TaxSelector.list_active()` -- la version con nombre crudo
  le atribuia lectura de `Tax` tambien a `ProductSelector.list_active()`). Corregido matcheando
  por `qualified_name` (`Clase.metodo`), mismo esquema que `extract_symbols()`. Verificado contra
  shop real: `trace_data_flow("Product")` reconstruye 28 accesos backend, `ProductSerializer`,
  endpoint real, 6 consumidores frontend incluyendo `shopService.js`. `field_verified` es honesto
  (no optimista): `Product.name` -> `true`, `Product.image` -> `false` (las imagenes viven en
  `ProductImage`, no en `Product` directo -- el ejemplo del plan original no es literalmente
  reproducible en este esquema, reportado tal cual). Grafo: 9550/16953 -> 9550/18217 (+1264
  aristas). Disponible via `project-graph data-flow <Model|Model.campo>`. 65/65 tests. Detalle
  completo en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 4 "Contract Graph Frontend<->Backend" en project_knowledge_graph (2026-08-10, prompt
  maestro de 22 fases -- solo FASE 4 ejecutada, checkpoint PASS, sin avanzar a FASE 5):** conecta
  `CONSUMES_ENDPOINT`/`USES_STORE` a nivel de `Symbol` (no solo archivo), agrega `USES_COMPOSABLE`
  y `Endpoint -SERIALIZES-> Serializer`. **3 defectos reales encontrados y corregidos contra el
  repo real:** (1) `USES_STORE` tenia **0 aristas en todo el grafo** -- matching por substring de
  un nombre derivado del hook contra el `store_id` de negocio, strings sin relacion garantizada;
  fix con `hook_name` real + matching exacto. (2) la capa de "custom API wrapper" del proyecto
  (`frontend/src/services/**/*.js`, 10 archivos, 69 llamadas reales con el patron encadenado
  `useApi().get(url)`) era invisible para el grafo -- ni se detectaban sus llamadas API ni
  generaban `Symbol` (son objetos exportados planos, no Pinia stores). (3) encontrado verificando
  el fix anterior: el matching de URL->Endpoint comparaba por "ultimo segmento coincide", lo que
  matcheaba `renting/equipment/{uuid}/check-availability/` contra un endpoint de `auth` no
  relacionado solo por compartir el substring `"availability"` -- corregido a matching por
  PREFIJO real de router. Verificado end-to-end contra la cadena real
  `availabilityService.check` -> `endpoint:api/v1/renting/equipment` ->
  `EquipmentViewSet.check_availability` + sus Serializers. Grafo: 9481/15863 -> 9550/16953. 60/60
  tests. Detalle completo en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md`
  seccion 11.
- **FASE 3 "Frontend Symbol Intelligence" en project_knowledge_graph (2026-08-10, nuevo prompt
  maestro de 22 fases -- solo FASE 3 ejecutada, checkpoint PASS, sin avanzar a FASE 4):** `Symbol`
  (mismo node type que Python, no uno nuevo) se extiende a `.vue`/`.js`/`.ts` via
  `scanner/frontend_scanner.py::extract_frontend_symbols()` -- extraccion heuristica (regex +
  balance de parentesis/llaves, sin parser JS real) de funciones/const-arrow/computed/watch/
  lifecycle hooks + metodos `actions:`/`getters:` de Pinia option-stores. Reusa el 100% de la
  maquinaria `CONTAINS` de `builder.py` ya existente para Python (sin tocar esa logica). 2 bugs
  reales encontrados y corregidos: (1) el overlap-skip disenado para que `catch`/`finally`
  anidados en un metodo de store no se contaran como simbolos propios tambien suprimia funciones
  nombradas legitimamente anidadas dentro de un composable exportado (el patron dominante real de
  este proyecto, ver `useOperationTracking.js`) -- corregido acotando el overlap-skip solo a
  donde hace falta; (2) lifecycle hooks (`onMounted`/`onUnmounted`) tambien matcheaban el patron
  de nombre de `event_handler`, clasificacion redundante -- corregido. Verificado con lineas
  exactas contra 3 archivos reales de Renting/Availability (`availabilityStore.js`,
  `useOperationTracking.js`, `AvailabilityCard.vue`) + verificacion sistemica sobre los 2549
  Symbol frontend reales (0 rangos invertidos, 0 nombres vacios/palabras reservadas). Grafo:
  6932/10833 -> 9481/15863 (nodos/aristas). 51/51 tests. Detalle completo en
  `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.
- **FASE 2 "Contract Graph" en project_knowledge_graph (2026-08-10, continuacion del rediseno
  "Site Knowledge Graph"):** agregados los node types `WebSocketRoute` y `EnvVar` + aristas
  `IMPLEMENTED_BY` (`Endpoint->Symbol`, reproduce el ejemplo exacto del usuario: `GET /api/v1/
  renting/availability/` -> `AvailabilityViewSet.list` con lineas reales; `WebSocketRoute->
  Consumer`) y `USES_ENV` (`File->EnvVar`, reproduce el otro ejemplo del usuario:
  `AI_SUPPORT_CHAT_ENABLED` -> que archivo la lee). De los 7 sub-tipos de "Contract Graph" del
  plan original solo se construyeron estos 2 -- PayloadSchema/ResponseSchema ya cubiertos por
  `Serializer`, EventContract/DatabaseContract quedaron fuera (ambiguos, parcialmente cubiertos
  por `Signal`/`DEPENDS_ON`), documentado en el codigo, no omitido en silencio. **Bug real
  encontrado corriendo contra el repo, no contra un fixture:** el scanner de rutas WebSocket
  solo reconocia `path()`, y `operations/routing.py` (el unico consumer real de esa app,
  `OperationTrackingConsumer`) usa `re_path()` -- se perdia esa ruta en silencio hasta
  verificar contra datos reales. Corregido y verificado: las 4 rutas WebSocket reales del
  proyecto (incluida `ws/support/chat/` -> `SupportChatConsumer`, el mismo consumer auditado
  en vivo en la sesion de diagnostico del chatbot este mismo dia) quedan correctamente
  linkeadas. Grafo completo: 6860/10283 -> 6932/10833 (nodos/aristas). 7 tests nuevos, 40/40
  pasan. Detalle en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` secciones
  4 y 11.

- **FASE 1 -- File/Symbol/CONTAINS en project_knowledge_graph (2026-08-10, continuacion del
  rediseno "Site Knowledge Graph"):** agregadas las entidades `File` (un nodo por archivo
  escaneado, con language/lines/hash/role) y `Symbol` (un nodo por funcion/metodo **Python**
  con `qualified_name` tipo `Clase.metodo` y rango de lineas exacto `start_line`/`end_line`),
  mas la arista `CONTAINS` (File->Symbol, File->cualquier nodo existente en ese archivo,
  Clase->su propio metodo). Objetivo explicito del usuario: que la IA reciba
  "AvailabilityEngine.calculate_availability() lineas 82-147", no solo el nombre del archivo.
  `CodeSegment` (item separado en el plan del usuario) se dejo **fuera a proposito**: con un
  scanner de una sola pasada, sin tracking de identidad cross-commit, seria casi identico a
  `Symbol` -- documentado como decision de alcance, no como omision. Frontend NO tiene `Symbol`
  todavia (ya tenia granularidad de archivo via FrontendComponent/PiniaStore/Composable/Route).
  Verificado en vivo contra el repo real: 1161 nodos File, 3778 nodos Symbol, el grafo completo
  paso de 1923/3291 a 6860/10283 nodos/aristas. La CLI existente (`project-graph node <nombre>`)
  ya funciona con estos nodos nuevos sin ningun cambio -- confirmado consultando
  `RentalOperationViewSet.dashboard` y obteniendo lineas 31-32 reales. 7 tests nuevos agregados
  (unit tests de `extract_symbols()`/`file_stats()` + integracion contra el grafo real), 33/33
  pasan. Detalle completo en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md`
  secciones 4 y 11.

- **FASE 0 -- desacoplamiento arquitectonico ai_engine <-> project_knowledge_graph
  (2026-08-10, a peticion del usuario -- rediseno hacia "Site Knowledge Graph" +
  futuro "AI Editor Runtime", separados del chatbot de soporte):** el usuario definio
  una nueva regla arquitectonica -- **"AI Engine no conoce ni importa project_knowledge_graph"
  y "project_knowledge_graph no conoce ni depende de ai_engine"** -- y pidio ejecutar
  primero la separacion fisica antes de construir nada nuevo (File/Symbol/Contract/Change
  Graph son roadmap futuro, no ejecutados en esta sesion). Se retiraron TODOS los imports
  reales de `project_knowledge_graph` desde `ai_engine` (verificado con un test de
  contrato AST-based que recorre todo `ai_engine/*.py`): `main.py` (`/impact`, `/breakage`,
  `/graph/node`, `/graph/impact`, gobernanza de `/refresh` -- ahora devuelven estructura
  vacia valida o 501 explicito, no error), `planner.py` (pasos 2/5/6/8/9/10 del pipeline de
  17 pasos -- ahora stubs locales que devuelven "sin datos"), `graph.py` (import que
  resulto ser codigo muerto, nunca se usaba), `incremental_updater.py` (ya no delega nada a
  PKG, solo reconstruye APP_MEMORY/AI_MANIFESTS/indices especializados, con deteccion de
  cambios via git diff propia, duplicada a proposito). `tools/graph_tools.py`
  (`GraphImpactAnalysisTool`) se **borro por completo** -- no se degrado, se elimino: era
  una capacidad de arquitectura/ingenieria expuesta al chat de soporte via el intent
  "architecture_impact" (conectado 2026-08-04), desregistrada de `tools/__init__.py`,
  `capabilities/registry.py` y `agents/profiles/admin_agent.yaml`. `pkg_bootstrap.py`
  tambien se borro (ya no hace falta agregar `project_knowledge_graph` al sys.path de
  ningun proceso de `ai_engine`). **Hallazgo real encontrado durante la ejecucion, no en
  el pedido original:** `memory_builder.py`/`ai_manifest.py`/`specialized_retrieval.py`
  leen `ai_engine/PROJECT_MAP.json` directo de disco (nunca importaron PKG) pero ese
  archivo ya NO se regenera desde ningun lado tras este cambio -- queda como foto estatica;
  documentado explicitamente como limitacion pendiente (no resuelta con un scanner
  duplicado sin que se pida) en `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md`, que
  tiene la matriz exacta de que se quito y donde debe reubicarse (futuro AI Editor Runtime).
  Verificado con la suite de tests existente (15/19 pasan, resto bloqueado por
  dependencias de terceros ausentes en el host, no por este cambio) mas 2 tests de
  contrato nuevos (uno en `ai_engine/tests/`, uno en `project_knowledge_graph/tests/`) que
  fallan si alguien vuelve a introducir el acoplamiento.

- **Auditoria E2E del chatbot de soporte -- causa raiz real: contenedor
  `frontend` caido 18h sin restart policy (2026-08-10, "AUDITORIA ENTERPRISE
  — CHATBOT SINTEL" a peticion del usuario):** sintoma reportado: "el chat
  aparece activo, no inicia conversacion, no genera respuestas de IA".
  Metodologia: NO se asumio Vite como causa -- se demostro con evidencia real
  en cada capa (logs de Django con las trazas `[WS]`/`[CHAT]`/`[AI_BRIDGE]` ya
  instrumentadas en `support/consumers.py`/`support/services/ai_bridge.py` de
  auditorias previas, mas reproduccion en vivo con browser real logueado como
  cliente QA). **Causa raiz encontrada:** `docker ps -a` revelo que
  `ecommerce_sintel_frontend` estaba `Exited (1)` desde 18 horas antes --
  `Error: EIO: i/o error, stat '/app'` (el mismo bug de inestabilidad
  bind-mount Docker Desktop/Windows + chokidar ya documentado y "mitigado" con
  `CHOKIDAR_USEPOLLING=true` el 2026-08-08, que igual volvio a tumbar el
  proceso Node completo por una excepcion no capturada). Como el servicio
  `frontend` en `docker-compose.yml` NUNCA tuvo `restart: unless-stopped` (a
  diferencia de `django`/`celery_worker`/etc.), el contenedor se quedo caido
  sin que nada lo notara ni lo reiniciara -- toda la SPA (incluido el chat)
  inalcanzable durante ese tiempo, consistente con el sintoma reportado.
  **Una vez reiniciado el contenedor, se verifico en vivo que TODA la cadena
  real funciona correctamente:** login real -> WebSocket conecta con JWT real
  (`ws/support/chat/`) -> `SupportChatConsumer` persiste el mensaje -> AI
  Engine responde (~11s de latencia, uso una Tool, escalo a humano
  correctamente via `ai_paused=True` cuando correspondia) -> el widget
  renderiza el mensaje propio y la respuesta de la IA en tiempo real. Ningun
  otro hallazgo de codigo: routing ASGI, `JWTAuthMiddlewareStack`,
  `is_ai_mode_active()`, `ai_bridge.py` y el frontend (`SupportChatWidget.vue`)
  estan todos correctos -- el `apiBase`/`wsBase` del widget ya cae de forma
  segura a `http://localhost:8000` cuando `VITE_API_BASE_URL` no esta seteada
  (no es un bug, es el fallback documentado en el propio codigo).
  **Correccion aplicada:** se agrego `restart: unless-stopped` al servicio
  `frontend` en `docker-compose.yml` (igualandolo al resto de servicios) para
  que un crash futuro de este tipo se autorecupere en vez de quedar silencioso
  indefinidamente. **Hallazgo secundario, no corregido (bajo impacto en dev):**
  el contenedor `nginx` tampoco esta corriendo (decision explicita de una
  sesion anterior, 2026-08-08, para no reiniciar `winnat` de Windows) -- no
  bloquea el chat en dev porque el widget nunca pasa por nginx (conecta
  directo a `localhost:8000`), pero si es relevante para paridad con
  produccion, donde SI hay que verificar `location /ws/` + `proxy_http_version
  1.1` + `Upgrade`/`Connection "upgrade"`.

- **Separacion de `project_knowledge_graph/` fuera de `ai_engine/` (2026-08-09,
  PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, ejecutado completo fase
  por fase con 2 checkpoints):** todo el analisis estructural del proyecto
  (`project_map.py`, `knowledge_graph.py`, `dependency_graph.py`,
  `incremental_updater.py`, `auditor.py`, y la familia Graphify --
  `agent_graph.py`/`docker_graph.py`/`documentation_graph.py`/
  `graph_validator.py`/`graph_visualizer.py`) se movio de `ai_engine/` (plano)
  a `ecommerce_sintel/project_knowledge_graph/` (modulo independiente, con
  capas propias: `scanner/`, `project_map/`, `knowledge_graph/` (+
  `enrichers/`), `dependency_graph/`, `incremental/`, `audit/`, `snapshots/`
  (nuevo -- historial ligero de cada run, antes no existia), `cli/` (nuevo --
  `python -m project_knowledge_graph.cli ...`), `tests/`, `data/`). Los 9
  archivos viejos en `ai_engine/` (los de arriba) se BORRARON -- ya no
  existen. `main.py`/`planner.py`/`graph.py`/`tools/graph_tools.py` importan
  project_knowledge_graph directo (via `ai_engine/pkg_bootstrap.py`, que
  agrega el modulo al sys.path -- necesario porque la imagen Docker de
  `sintel_ai` se construye con `context: ./ai_engine` y NUNCA contenia
  project_knowledge_graph, solo es visible dentro del contenedor via el mount
  read-only `.:/workspace:ro`). `ai_engine/incremental_updater.py` SI se
  mantuvo (ya no es un shim, es la integracion permanente: delega PROJECT_MAP/
  KG/DG a project_knowledge_graph pero sigue orquestando `APP_MEMORY`/indices
  especializados aca, que son responsabilidad de ai_engine). Verificado
  end-to-end contra el repo real varias veces (21 apps, ~1920 nodos KG, ~3290
  aristas, el caso de blast-radius de 'renting' que motivo la auditoria
  original sigue devolviendo el mismo resultado correcto). Durante la
  migracion se encontro y corrigio un bug real de resolucion de rutas
  (`Path(__file__).resolve().parents[N]` con N incorrecto) en los primeros 2
  enrichers escritos (`agents.py`/`docker.py`) que habria devuelto resultados
  vacios en silencio -- detectado por verificacion activa contra datos reales,
  no en revision pasiva. **Pendiente, no critico:** varios docs (`ai_engine/.AGENT/
  FLIJO_COMPLETO_IA_ENGINE.md`, `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md`,
  `docs/.AGENT/AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md`) todavia describen
  la arquitectura vieja (archivos planos en ai_engine/) y no se actualizaron en
  esta sesion.

- **Auditoria de alineacion de `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md`
  (2026-08-06, a peticion del usuario -- "valida y audita mi app core, actualiza
  documentacion"):** auditoria pura (sin cambios de codigo), comparo el doc
  contra `models.py`/`signals.py`/`services/selectors.py`+`commands.py`/
  `api/views.py`+`serializers.py`/migraciones/`dashboard/api/views.py`/consumo
  frontend. Hallazgo mas importante: **el documento afirmaba que `HomeCardGroup`
  no tenia signal de invalidacion de cache propio ("gap conocido, decision de
  diseno intencional") -- eso es falso**, `core/signals.py` SI registra
  `invalidate_home_feed_on_card_group_change` desde hace tiempo (no se pudo
  determinar exactamente cuando, no hay entrada de "Cambios Recientes" que lo
  mencione); a la fecha de esta auditoria los 12 modelos con cache en `core`
  tienen signal, ninguno depende solo de invalidacion manual. Otros hallazgos
  de deriva documental (sin bug real detras, solo doc desactualizado): 3
  migraciones (0001-0026) fueron squasheadas (DT-M18, 2026-07-30) y el
  documento seguia listandolas individualmente; `HomeCard.badge_text` +
  `CARD_TYPE_LOGO` y `HomeCardGroup.glass`/`.hover` + `LAYOUT_LOGOS`/`MARQUEE`
  (todos desde migr. 0020, 2026-06-30) nunca se documentaron; `core/api/internal_ai.py`
  (fachada AI Engine, 9 vistas bajo `/api/v1/internal/ai/core/*`) no existia en
  el doc; el endpoint `site-config` gano un bloque `seo` (meta_title/
  meta_description/og_image desde `organization.SeoSettings`) consumido
  client-side por `HomeView.vue` via `useSeo()`, tampoco documentado;
  `TrustSection.vue` ya no existe como archivo (consolidado en
  `HomeRenderer.vue`, compartido entre Home publica y Vista Previa del panel
  admin). Se confirmo (sin corregir aqui, ya corregido el 2026-08-05 en Sprint 2
  de la auditoria transversal) que `AboutUsConfig`/`BrandSliderConfig` ganaron
  `is_active` + `shared.models.SingletonMixin` para cerrar una condicion de
  carrera real de "2 requests concurrentes crean 2 filas singleton" -- el doc
  anterior describia la ausencia de esa proteccion como decision de diseno
  cuando en realidad era el bug. **Gaps que quedan abiertos, documentados pero
  no corregidos:** `core/tests/test_models_and_signals.py` no cubre las signals
  de 6 de los 12 modelos con cache (`HomeCard`, `HomeCardGroup`,
  `FooterCTAConfig`, `FooterGroup`, `BrandSliderItem`/`Config`,
  `AboutUsConfig`/`Value`). Doc completamente reescrito en las secciones
  afectadas; ver "Cambios Recientes" del doc de `core` para el detalle completo.

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
