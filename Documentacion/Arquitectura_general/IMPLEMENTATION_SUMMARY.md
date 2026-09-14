# IMPLEMENTATION SUMMARY — Sintel E-Commerce REST

> **Punto de entrada:** este documento es el paso 3b (fallback) del flujo de consulta jerarquico
> definido en `ecommerce_sintel/.AGENT.md` ("FLUJO OBLIGATORIO ANTES DE MODIFICAR CODIGO") —
> usarlo cuando la app exacta de una tarea no se conoce de antemano. Si SI se conoce la app,
> ir directo a su fila en la tabla "DOCUMENTOS DE REFERENCIA POR MODULO" de `.AGENT.md`.

Ultima revision: 2026-08-12 (v16 — cierre completo de las 60 fases del plan "AI Change Proposal
Engine" (FASE 24-60), construido estrictamente sobre el "AI Editor Runtime" ya cerrado en v15).
`ai_editor/generation/` (24 submodulos) evoluciona el mecanismo de v15 (`PATCH SANDBOX`) en un
motor real de PROPUESTA: LLM + contexto MINIMO del grafo (nunca el grafo completo) ->
`PatchProposal` estructurada, validada capa por capa (sintaxis/scope/dependencias/contratos/
tests/documentacion/arquitectura/seguridad) antes de llegar a revision humana. `ai_editor/agent/`
(FASE 51-53, paquete nuevo) orquesta todo ese pipeline en una sola llamada
(`run_autonomous_change_loop()`) — **REGLA FINAL DE SEGURIDAD garantizada de forma ESTRUCTURAL,
no por convencion**: verificado por test AST que ese paquete nunca importa el modulo que sabe
promover al workspace real, asi que el estado mas avanzado que puede alcanzar es
`APPROVAL_REQUIRED`, nunca mas. Detalle completo fase por fase en
`ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` y checkpoint consolidado en
`ai_editor/.AGENT/AI_EDITOR_BASELINE.md`.
(A) **Primera vez en todo el desarrollo de `ai_editor` que se corrio contra un LLM REAL**
(FASE 51-53): Ollama local confirmado alcanzable en este entorno (`llama3.1:8b`, el default de
`ai_editor/llm/` cuando no se configura otro proveedor) — corrigio una afirmacion previa (desde
FASE 28) de que ningun LLM estaba disponible, nunca verificada hasta entonces. Hallazgo real, no
un bug: el modelo local de 8B no siempre produce JSON estructurado valido en pocos intentos —
`REJECTED` correcto y honesto (nunca se fabrico un patch), documentado como limitacion del
modelo, no del pipeline.
(B) **10 capas de validacion real antes de revision humana** (FASE 33-46), cada una con su gap
encontrado y corregido en la propia verificacion: Reconciliation (FASE 34, scope real vs
declarado) filtraba mal por severidad tras relajar un guardrail en FASE 38, corregido; Impact
Recheck (FASE 35) aproximaba mal el "impacto predicho" sumando 3 buckets que excluian
tests/docs/config, produciendo falsos BLOCK siempre — corregido capturando un baseline real via
`calculate_impact()`; Code Quality (FASE 36) corre `bandit` REAL (verificado instalado y
configurado, nunca asumido) contra los archivos que la propuesta toca, JS/Vue queda
`NOT_CONFIGURED` honesto (sin eslint instalado); Architectural/Dependency/Contract/Test/
Documentation-Awareness (FASE 37, 40-43) cruzan la propuesta contra reglas YA documentadas del
repo, nunca una regla inventada.
(C) **FASE 38 — unica relajacion de guardrail de seguridad de todo el plan, con confirmacion
explicita en 2 pasos del usuario**: permite que una propuesta escriba tambien sobre pasos
`REVIEW` (no-documentacion) y `RUN` del plan (antes solo `MODIFY`), habilitando cambios
cross-stack reales (backend + frontend + tests en una sola propuesta) — `.md` sigue
PERMANENTEMENTE excluido de escritura automatica, sin excepcion.
(D) **FASE 49 "Security Hardening" — auditoria real (no fabricada) de FASE 24-46**: 1 gap
genuino encontrado y corregido (`code_quality.py` sin el mismo boundary check anti-traversal que
el Patch Engine real ya tenia, riesgo practico bajo por estar mitigado aguas arriba, corregido
igual por defensa en profundidad). Limites verificados reales y activos:
`MAX_OPERATIONS_PER_PROPOSAL=20`, `MAX_PATCH_CONTENT_BYTES=5MB`, `MAX_SANDBOX_FILES=500`,
`DEFAULT_MAX_RETRIES=3`.
(E) **FASE 54-55 — confirmado real contra el repositorio real**, la unica escritura real de todo
el plan: comentario de 1 linea sobre `HomeCardGroupSelector.get_by_name`
(`core/services/commands.py`), contenido construido a mano (no por el LLM, decision explicita
del usuario para que la prueba fuera predecible) — `PROMOTE -> PROMOTED` (verificado leyendo el
archivo real) seguido de `ROLLBACK -> ROLLED_BACK` (verificado con SHA-256 completo del archivo,
identico byte a byte antes/despues, y `git diff` sin rastros). El archivo objetivo tenia trabajo
real del usuario sin commitear en otras lineas — comunicado antes de proceder, confirmado, y
quedo intacto.
449/449 tests + esta verificacion manual contra el repo real. `ai_editor` sigue sin poder
escribir sobre un checkout real salvo a traves de `promote_to_workspace()` (5 capas de guardrail,
`SECURITY_MODEL.md`), y `ai_editor/agent/` sigue sin poder LLEGAR a esa funcion (garantizado por
test AST, no por convencion).

> **Nota (2026-08-17):** el historial v1-v16 de arriba trackea especificamente el thread
> `ai_editor`/`project_knowledge_graph`. El thread paralelo del **AI Engine como Support Agent**
> (chatbot conversacional del Customer, `ai_engine/` FastAPI) tiene su propia seccion nueva —
> ver `### ai_engine` en "Apps y estado de implementacion" — y su propio historial de cierre en
> "Tareas pendientes" → "Completadas (2026-08-17 — Auditoria E2E de cierre del AI Engine /
> Support Agent)". Ambos threads son independientes (sin conexion directa entre `ai_editor` y
> `ai_engine`, verificado por test AST) y `ai_editor` sigue **CONGELADO** — sin fases nuevas.

<details>
<summary>Historial de versiones anteriores (v1-v15) — click para expandir</summary>

**v15 (2026-08-11 — cierre completo de las 24 fases (POST-GRAPH 0-23) del plan
"Evolucion de AI Editor Runtime", construido estrictamente sobre el Site Knowledge Graph ya
cerrado en v14). `ai_editor/` deja de ser un scaffold de solo lectura y gana un pipeline real
READ -> RESOLVE -> PLAN -> PROPOSE -> PATCH SANDBOX -> VALIDATE -> HUMAN APPROVAL -> COMMIT, con
escritura como la ULTIMA capa del sistema, nunca la primera, y solo detras de aprobacion humana
explicita:**
(A) **Frontera arquitectonica verificada por test**: `ai_editor -> graph_client -> graph_sdk ->
project_knowledge_graph` es el UNICO camino permitido (POST-GRAPH 1, `graph_client` como reexport
de solo lectura de `graph_sdk`, verificado con un test que camina el AST); `ai_editor` nunca
importa `ai_engine` ni viceversa, tambien verificado por test automatizado.
(B) **Cliente LLM independiente** (POST-GRAPH 2): submodulo `ai_editor/llm/` nuevo, sin depender
de `ai_engine` ni de ningun otro modulo — proveedor intercambiable via `AI_EDITOR_LLM_PROVIDER`
(Ollama local / OpenAI / Anthropic vía API key propia), `urllib` puro, la API key nunca se filtra
ni siquiera en errores HTTP (verificado con un 401 simulado).
(C) **Pipeline completo, cada capa con su gap real encontrado y corregido**: Change Resolver
exige coincidencia EXACTA de entidad, nunca difusa (POST-GRAPH 3, bug real de fuzzy-match
encontrado con "Equipment"); Change Plan + validacion contra disco real con resolucion de path
dual backend/frontend (POST-GRAPH 4-5); Patch Engine que aplica un `new_content` YA DECIDIDO —
deliberadamente SIN generacion automatica de codigo (POST-GRAPH 6); Sandbox aislado que copia
solo los archivos que el plan toca, nunca el repo completo, con limite de archivos/tamano y lista
de patrones sensibles excluidos (POST-GRAPH 7, endurecido en POST-GRAPH 18); Validacion Nivel 1
de sintaxis real (POST-GRAPH 8); Graph Reconciliation honestamente `NOT_IMPLEMENTED` (nunca un
`0` fingido) y deteccion de tests de impacto sin ejecutarlos (POST-GRAPH 9-10); Human Approval
Gate como punto de parada obligatorio (POST-GRAPH 11); Commit Control — `promote_to_workspace()`/
`rollback_promotion()` (POST-GRAPH 12); Audit con saneamiento real de secretos, bug de
sanitizacion parcial encontrado y corregido (POST-GRAPH 13); Autonomous Change Loop documentado,
NO orquestado automaticamente, mismo criterio de seguridad (POST-GRAPH 14); multi-step/DAG
diferido por falta de caso real de uso (no fabricado como si existiera) + Rollback real
(POST-GRAPH 15-16); Observabilidad con metricas honestas (POST-GRAPH 17).
(D) **Hardening y gap de seguridad mas significativo del plan**: auditoria real contra la lista
de riesgos del prompt maestro — symlinks verificados YA seguros (no era un gap), 3 gaps reales
corregidos: limite de tamano de patch, limite de archivos en sandbox, patrones sensibles
incompletos (POST-GRAPH 18). **POST-GRAPH 20**: `promote_to_workspace()` no verificaba en codigo
que la validacion de sintaxis hubiera pasado antes de escribir — dependia solo de que un humano no
aprobara por error un cambio con sintaxis rota. Corregido con un parametro `validation_report`
que rechaza estructuralmente (`VALIDATION_FAILED`) sin importar la aprobacion humana.
(E) **POST-GRAPH 21 — confirmado real contra el repositorio real** (no solo contra sandboxes de
prueba): ejecucion delegada al usuario via un script autocontenido; el primer intento produjo un
`SyntaxError` real por un bug del propio script de demo, y el guardrail de POST-GRAPH 20 lo
bloqueo correctamente antes de escribir nada — la primera vez que ese guardrail se probo contra un
error real, no un test. El segundo intento (corregido) completo el ciclo entero:
`PROMOTE -> PROMOTED` (archivo real modificado, verificado) seguido de
`ROLLBACK -> ROLLED_BACK` (archivo real restaurado, verificado), y una verificacion independiente
posterior via `git diff` confirmo cero cambios netos en el repositorio. POST-GRAPH 22 (cobertura
cross-stack) ya estaba cubierta por tests de integracion existentes; POST-GRAPH 23 (tabla de
readiness de las 15 preguntas del prompt maestro) verificada con datos reales sobre
`EquipmentViewSet.check_availability`.
257/257 tests. `ai_editor` sigue sin poder escribir sobre un checkout real salvo a traves de
`promote_to_workspace()`, con las 5 capas de guardrail descritas en `SECURITY_MODEL.md`.

**v14 (2026-08-11 — cierre completo de las 22 fases (FASE 0-21) del rediseno arquitectonico
"Site Knowledge Graph -> Change Intelligence -> AI Editor Runtime" para
`project_knowledge_graph`):**
(A) **FASES 3-9 — grafo estructural completo**: `Symbol` extendido a Vue/JS (Fase 3); Contract
Graph frontend<->backend a nivel de simbolo individual, `CONSUMES_ENDPOINT`/`USES_STORE`/
`USES_COMPOSABLE`/`SERIALIZES` (Fase 4); Data Flow Graph, `READS_FROM`/`WRITES_TO` de
`Model.objects.verbo()` real (Fase 5); Execution Graph, `TRIGGERS`/`QUEUES` de signals y Celery
tasks (Fase 6); Test Graph, `TESTS`/`VALIDATES` (Fase 7); Documentation Graph, `REFERENCES` desde
texto libre (Fase 8); Configuration/Infrastructure Graph, Docker/nginx/env (Fase 9).
(B) **FASES 10-13 — capa de consulta para asistir cambios**: `calculate_change_impact()` (Fase
10, impacto directo/indirecto categorizado + riesgo), `resolve_change()` (Fase 11, envelope
completo), `build_graph_context_packet()` (Fase 12, compresion miles->decenas de nodos para
consumo LLM), `graph_sdk` (Fase 13, fachada estable de 13 operaciones).
(C) **FASE 14 — `ai_editor/` (scaffold deliberado, NO funcional en ese momento)**: paquete nuevo
`ecommerce_sintel/ai_editor/`; solo `graph_client/` (wrapper de solo lectura) tenia logica real —
generar/aplicar parches de codigo automaticamente (`patch/`) se dejo deliberadamente sin
implementar todavia. **Superado en v15**: el plan POST-GRAPH 0-23 completo ese trabajo.
(D) **FASES 15-18 — deteccion, validacion y observabilidad**: deteccion de simbolos cambiados via
`git diff` real (Fase 15); Change Validation Report — impacto + tests requeridos + consistencia de
grafo/contratos sobre el diff actual (Fase 16); diseno documentado (no codigo) del Autonomous
Change Loop, con el mismo criterio de seguridad de (C) (Fase 17); auditoria real de consultas via
`graph_sdk`, nunca persiste datos de nodo sensibles (Fase 18).
(E) **FASES 19-21 — consolidacion, limpieza y validacion final**: 5 defectos reales de
documentacion corregidos en `ARQUITECTURA_COMPLETA_GRAFO.md` (Fase 19); 4 documentos vivos de
`ai_engine/.AGENT/` con referencias desactualizadas a modulos retirados corregidas (Fase 20);
rebuild completo real + suite de tests corrida dos veces, 0 regresiones (Fase 21).
Grafo real final: 6932/10833 (2026-08-10, post Fase 2) -> **9575/20335** (nodos/aristas,
verificado en Fase 21) — 21 apps Django, 150 endpoints, 1161 archivos, 6396 Symbol. **120/120
tests pasan.** `project_knowledge_graph` sigue sin conocer ni importar `ai_engine`, verificado por
test automatizado (Regla 0 del rediseno).

**v13 (2026-08-10 — auditoria E2E del chatbot de soporte + FASES 0-2 del rediseno "Site
Knowledge Graph"):**
(A) **Causa raiz real de "el chatbot no responde"**: el contenedor `frontend` estaba `Exited(1)`
desde 18 horas antes (`Error: EIO`, el mismo bug de bind-mount Docker Desktop/Windows +
chokidar ya documentado, sin `restart` policy para autorecuperarse) — NO fue un bug de codigo
(WebSocket/JWT/Channels/`ai_bridge`/AI Engine verificados funcionando correctamente en vivo tras
reiniciar el contenedor). Corregido: `restart: unless-stopped` agregado al servicio `frontend`.
(B) **FASE 0 — `ai_engine` desacoplado por completo de `project_knowledge_graph`**: nueva regla
arquitectonica ("AI Engine no conoce ni importa project_knowledge_graph") — `GraphImpactAnalysisTool`
eliminado (no degradado, incluida su conexion como intent de chat `architecture_impact`),
`pkg_bootstrap.py` eliminado, `main.py`/`planner.py`/`graph.py`/`incremental_updater.py`
degradados a stubs locales que ya no importan el grafo.
(C) **FASE 1 — entidades `File`/`Symbol`**: la IA ya puede recibir "`Clase.metodo()` lineas N-M",
no solo el nombre del archivo — arista `CONTAINS`.
(D) **FASE 2 — "Contract Graph"**: entidades `WebSocketRoute`/`EnvVar` + aristas `IMPLEMENTED_BY`
(`Endpoint->Symbol`, `WebSocketRoute->Consumer`) y `USES_ENV` (`File->EnvVar`).
Grafo real: 1923/3291 (nodos/aristas, 2026-08-09) -> 6932/10833 (2026-08-10, post Fase 2).

Ultima revision: 2026-08-10 (v12 — auditoria cruzada contra las AUDITORIA/29-33, repasos de
backlog 31-32, plan de separacion del grafo de conocimiento y hallazgo de 2 modulos nuevos no
listados: `sms_bridge` y `project_knowledge_graph`). Cambios reales documentados en esta version:
(1) **`/api/v1/health/` ya no es falso positivo** (AUDITORIA/29, P1-CRITICO): `health_check` en
`ecommerce/urls.py` devolvia `{"status":"ok"}` incondicionalmente sin verificar nada; ahora reusa
`SecuritySelector.get_health_snapshot()` y devuelve 503 si `db` o `redis` fallan — Docker reinicia
el contenedor correctamente. (2) **`celery_beat` gano su propio HEALTHCHECK** (AUDITORIA/31):
antes no tenia ningun check, ahora usa `grep -a -l celery /proc/[0-9]*/cmdline` — mejora real
sobre cero monitoreo para las 2 `PeriodicTask` que dependen de el. (3) **Indices de BD agregados**
(AUDITORIA/31): `NotificationLog` (temple_slug + GIN sobre payload_context) y `ChatRoom` (status,
ai_paused, updated_at, is_deleted compuesto) — tablas filtradas en cada corrida de los 4
scanners proactivos sin ningun indice previo. (4) **Heartbeat WebSocket en soporte** (AUDITORIA/31):
ping/pong de aplicacion cada 25s en `SupportChatWidget.vue`/`SupportDashboardView.vue` +
`support/consumers.py`; sin esto, conexiones zombie podian quedar en "en linea" indefinidamente.
(5) **Preferencias de mensajes proactivos de IA** (AUDITORIA/32):
`ai_proactive_room_message_task` ahora respeta `UserNotificationPreference` (opt-out identico
al resto de canales). (6) **Referencias a `OperationTicketSelector` corregidas** (AUDITORIA/32):
clase inexistente referenciada en `operations/models.py`, `serializers.py` y doc de arquitectura;
nombre real es `OperationSelector`. (7) **Backup automatizado corregido** (AUDITORIA/33): tarea
Windows corria como `SYSTEM` sin acceso al daemon Docker; reinstalada como `Administrator` y
verificada con restauracion completa (dump + media, snapshot preventivo, Django `healthy`
post-restauracion). (8) **Reinicio autorizado de cuentas de produccion** (2026-08-04): borrado
logico de 3 cuentas; 1 cuenta admin restaurada; contenedor permanecio `healthy`. (9) **Modulo
`sms_bridge` detectado** (no listado en ninguna version anterior): puente HTTP<->modem GSM SIM5360
(Movistar Colombia, COM5) corriendo en el HOST Windows, fuera de Docker — permite al contenedor
Django enviar SMS sin poder abrir un puerto COM de Windows directamente; ver seccion nueva abajo.
(10) **Modulo `project_knowledge_graph` detectado** (no listado en ninguna version anterior):
separacion del grafo de conocimiento del `ai_engine` iniciada 2026-08-08; la estructura de
directorios ya existe fisicamente (`scanner/`, `project_map/`, `knowledge_graph/`,
`dependency_graph/`, `incremental/`, `audit/`, `snapshots/`, `cli/`); ver seccion nueva abajo.
Las secciones v1-v11 se conservan como registro historico al final del documento.

> **Nota sobre esta version (v12):** auditoria cruzada contra el estado real del proyecto a
> 2026-08-10: AUDITORIA/29-33 (observabilidad, backup, produccion), repasos de backlog 31-32
> (quick-wins, correcciones latentes), plan de separacion del grafo de conocimiento (2026-08-08),
> y hallazgo de 2 modulos nunca documentados (`sms_bridge`, `project_knowledge_graph`). El
> encabezado de version captura todos los cambios reales. Las versiones v1-v11 se conservan como
> registro historico en "Tareas pendientes > Completadas". Las secciones "Correcciones y mejoras
> aplicadas" y "Cambios recientes" al final del documento son **registro historico** de versiones
> previas (2026-06-19 en adelante) — se conservan como bitacora, no como estado actual.

</details>

---

## Mapa de Documentacion por App

Cada app de negocio mantiene su propio documento de arquitectura en `.AGENT/docs/`.
El AI Engine los carga automaticamente en cada sesion.
Actualizar el documento de la app afectada despues de cada cambio estructural.

| App | Documento de Arquitectura | Estado (2026-08-10) |
|-----|--------------------------|-----------|
| `accounts` | [ARQUITECTURA_COMPLETA_ACCOUNTS.md](../../ecommerce_sintel/accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md) | Sincronizado 2026-07-09 — probablemente afectado por el rediseno de Auth (2026-07-17), no releido desde entonces |
| `cart` | [ARQUITECTURA_COMPLETA_CART.md](../../ecommerce_sintel/cart/.AGENT/docs/ARQUITECTURA_COMPLETA_CART.md) | Sincronizado 2026-07-03, no releido desde entonces |
| `core` | [ARQUITECTURA_COMPLETA_CORE.md](../../ecommerce_sintel/core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md) | Sincronizado 2026-07-09 — auditoria AUDITORIA/26 sin hallazgos (2026-08-02) |
| `dashboard` | [ARQUITECTURA_COMPLETA_DASHBOARD.md](../../ecommerce_sintel/dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md) | Creado 2026-07-03, no releido desde entonces |
| `ecommerce` (base) | [ARQUITECTURACOMPLETA_SETTING.md](../../ecommerce_sintel/ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md) | No releida en ninguna pasada reciente |
| `inventory` | [ARQUITECTURA_COMPLETA_INVENTORY.md](../../ecommerce_sintel/inventory/.AGENT/docs/ARQUITECTURA_COMPLETA_INVENTORY.md) | No releido en ninguna pasada reciente |
| `kyc` | [ARQUITECTURA_COMPLETA_KYC.md](../../ecommerce_sintel/kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md) | **App nueva, no listada en versiones anteriores** — verificacion de identidad (2026-07-06) |
| `marketing` | [ARQUITECTURA_COMPLETA_MARKETING.md](../../ecommerce_sintel/marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md) | AUDITORIA/27 (2026-08-02): ImportError P0 + P1 + P2 corregidos |
| `notifications` | [ARQUITECTURA_COMPLETA_NOTIFICATIONS.md](../../ecommerce_sintel/notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md) | Actualizado — gano indices BD (2026-08-03, AUDITORIA/31): `template_slug` + GIN sobre `payload_context` |
| `operations` | [ARQUITECTURA_COMPLETA_OPERATIONS.md](../../ecommerce_sintel/operations/.AGENT/docs/ARQUITECTURA_COMPLETA_OPERATIONS.md) | AUDITORIA/28 (2026-08-03) — referencias a clase inexistente `OperationTicketSelector` corregidas (nombre real: `OperationSelector`) |
| `organization` | [ARQUITECTURA_COMPLETA_ORGANIZATION.md](../../ecommerce_sintel/organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md) | **App nueva** — AUDITORIA/25 (2026-08-02). `organization/CLAUDE.md` dice "Fase 3 de 9" pero los 8 recursos estan operativos — sigue sin corregir |
| `security` | [ARQUITECTURA_COMPLETA_SECURITY.md](../../ecommerce_sintel/security/.AGENT/docs/ARQUITECTURA_COMPLETA_SECURITY.md) | **App nueva** — AUDITORIA/23 (2026-08-02). AUDITORIA/29: `get_health_snapshot()` ahora reusado por `/api/v1/health/` |
| `seo` | [ARQUITECTURA_COMPLETA_SEO.md](../../ecommerce_sintel/seo/.AGENT/docs/ARQUITECTURA_COMPLETA_SEO.md) | **App nueva** — creada 2026-07-31, metaetiquetas del `<head>` |
| `orders` | [ARQUITECTURA_COMPLETA_ORDERS.md](../../ecommerce_sintel/orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md) | Sincronizado 2026-07-09 — "Shop Operations" + FSM picking/packing/despacho/entrega |
| `payment` | [ARQUITECTURA_COMPLETA_PAYMENT.md](../../ecommerce_sintel/payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md) | Sincronizado 2026-07-13 — migracion API Wompi (ADR-001, 10 fases) |
| `quotes` | [ARQUITECTURA_COMPLETA_QUOTES.md](../../ecommerce_sintel/quotes/.AGENT/docs/ARQUITECTURA_COMPLETA_QUOTES.md) | Vigente — sistema CPQ/cuestionarios |
| `renting` | [ARQUITECTURA_COMPLETA_RENTIG.md](../../ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md) | **Pendiente propagar** los 3 incidentes de 2026-07-29 (ver "Tareas pendientes") |
| `shop` | [ARQUITECTURA_COMPLETA_SHOP.md](../../ecommerce_sintel/shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md) | No releido en profundidad desde 2026-07-03 |
| `sms_bridge` | *(sin doc propio aun)* | **Modulo nuevo detectado 2026-08-10** — puente HTTP<->modem GSM, corre en HOST Windows fuera de Docker; ver seccion dedicada abajo |
| `support` | [ARQUITECTURA_COMPLETA_SUPPORT.md](../../ecommerce_sintel/support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md) | Actualizado 2026-07-31 (AUDITORIA/15). 2026-08-03 (AUDITORIA/31): indices BD + heartbeat WS + CHANNEL_LAYERS con capacity/expiry explicitos |
| `technical_services` | [ARQUITECTURA_COMPLETA_SERVICES.md](../../ecommerce_sintel/technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md) | Sincronizado 2026-07-09 — checkout en modal + `ServiceOperation` (FSM post-pago) |
| `users` | [ARQUITECTURA_COMPLETA_USER.md](../../ecommerce_sintel/users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md) | Sincronizado 2026-07-09 |
| `project_knowledge_graph` | [ARQUITECTURA_COMPLETA_GRAFO.md](../../ecommerce_sintel/project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md) | **Modulo independiente, rediseno de 22 fases completo y verificado 2026-08-11** — separacion fisica de `ai_engine` cerrada (FASE 0); `ai_engine` no lo importa en absoluto, verificado por test; grafo estructural completo (Contract/Data Flow/Execution/Test/Documentation/Configuration Graph, FASES 1-9); capa de consulta para asistir cambios (`calculate_change_impact`/`resolve_change`/`graph_sdk`, FASES 10-13); deteccion/validacion/observabilidad de cambios (FASES 15-18); documentacion consolidada y limpia (FASES 19-20); 9575 nodos/20335 aristas reales, 120/120 tests; ver seccion dedicada abajo y `SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md` para el reporte de cierre completo |
| `ai_editor` | [AI_EDITOR_BASELINE.md](../../ecommerce_sintel/ai_editor/.AGENT/AI_EDITOR_BASELINE.md) | **Plan de 24 fases (POST-GRAPH 0-23) completo y verificado 2026-08-11** — de scaffold de solo lectura a pipeline funcional READ->RESOLVE->PLAN->PROPOSE->PATCH SANDBOX->VALIDATE->HUMAN APPROVAL->COMMIT; frontera `ai_editor -> graph_client -> graph_sdk -> project_knowledge_graph` verificada por test AST, nunca importa `ai_engine`; LLM propio intercambiable (Ollama/OpenAI/Anthropic) sin depender de otros modulos; sin generacion automatica de codigo (el `new_content` de un patch lo decide un humano); `promote_to_workspace()` con 5 capas de guardrail independientes, **confirmado PROMOTE+ROLLBACK reales contra el repositorio real** (POST-GRAPH 21, no solo contra sandboxes de prueba); 257/257 tests; ver `ai_editor/.AGENT/SECURITY_MODEL.md` para el modelo de seguridad completo |
| Frontend | [ARQUITECTURA_COMPLETAFRONEND.md](../../ecommerce_sintel/frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md) | **Pendiente propagar** 2 bugs de cards de 2026-07-29 (ver "Tareas pendientes") |


### Regla de actualizacion

Cuando se modifica o crea logica en una app, agregar al final del doc de esa app:

```markdown
## Cambios Recientes

### [fecha] Titulo del cambio
- Que cambio y por que
- Archivos afectados
- Contrato de API si cambio
```

---

## Arquitectura general

El proyecto es una API-first SaaS con frontend SPA desacoplado.

```
Cliente (navegador)
    |
    +-- Vue.js 3 SPA (Vite) --- /panel/*  (admin)
    |                       --- /         (landing / tienda / alquiler / servicios)
    |
    +-- HTTP / WebSocket
    |
Nginx (reverse proxy, puerto 80)
    |
    +-- /api/*  -> Daphne ASGI (puerto 8000) -> Django 5 + DRF
    +-- /ws/*   -> Django Channels (WebSocket)
    |
PostgreSQL 16  +  Redis 7.2  +  Celery  +  Celery Beat

AI Engine (FastAPI, puerto 8100) + ChromaDB (8200) + Ollama (11434) — contenedores
separados, no forma parte del request path de la tienda. Dos motores en un solo
servicio (2026-07-16, "AI Core", 8 fases): (a) generacion/validacion de codigo asistida
(el uso original, sin auth, solo dev); (b) `POST /chat` conversacional con JWT real de
Django, Tool Registry (29 Tools) + Agent Profiles (9 agentes) + confirmacion humana
para escrituras — usado por el widget de soporte web y WhatsApp via Django (el motor
nunca se expone directo al cliente). Detalle completo NO se repite aqui — ver
`ai_engine/.AGENT/GUIA_USO.md` (uso practico), `FLIJO_COMPLETO_IA_ENGINE.md`
(arquitectura) y `PLAN_DE_ACCION_AI_CORE.md` (historia de las 8 fases).
```

**Stack (version real verificada 2026-07-03):**

| Capa | Tecnologia |
|------|-----------|
| Backend | Django **5.2.13** + Django REST Framework |
| API schema | drf-spectacular (OpenAPI 3) |
| Auth | simplejwt — email como USERNAME_FIELD |
| Real-time | Django Channels + channels_redis |
| Async tasks | Celery + django_celery_beat |
| Payments | Wompi Colombia (widget hospedado, firma SHA256) + Nequi Push + COD — ver app `payment` |
| Frontend | Vue 3 + Vite + Pinia + Vue Router + Axios |
| DB | PostgreSQL 16 |
| Cache/Broker | Redis 7.2 |
| Proxy | Nginx 1.26 |
| AI Engine | FastAPI + ChromaDB + Ollama (auditoria/generacion de codigo, no parte del checkout) |

---

## RBAC — Control de acceso

> **[CORREGIDO 2026-07-03]** Toda esta seccion describia un campo `User.role` (ADMIN=1, CUSTOMER=2,
> VENDOR=3, TECHNICIAN=4) que **no existe en el codigo**. Fue eliminado en un refactor DDD anterior
> (ver `users/CLAUDE.md`: *"role (ADMIN/CUSTOMER/VENDOR/TECHNICIAN) — ELIMINADO — usar
> is_staff/is_superuser + accounts.UserProfile.user_type"*). Verificado leyendo `users/models.py`
> directamente: `User` solo tiene `email, is_active, is_staff, is_verified, date_joined` (+ lo
> heredado de `PermissionsMixin`/`SintelBaseModel`). Reescrito con el modelo real.

### Modelo de usuario real

```
users.models.User (AbstractBaseUser + PermissionsMixin + SintelBaseModel)
  email, is_active, is_staff, is_superuser, is_verified, date_joined, uuid, is_deleted
  # SIN campo role. SIN first_name/last_name (viven en accounts.UserProfile).

accounts.models.UserProfile (OneToOneField -> user.profile)
  first_name, last_name, phone_number, profile_picture, user_type
  user_type in {CUSTOMER, TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR, TRANSPORTER, ACCOUNTANT}
```

- **Admin real:** `is_staff=True AND is_superuser=True` — solo via `createsuperuser` CLI, la API nunca los crea.
- **Clasificacion de usuarios regulares:** `accounts.UserProfile.user_type` (no un campo en `User`).

### TechnicianProfile (vive en `accounts`, no en `users`)

- `user`: OneToOneField a `User`, `related_name='technician_profile'` (singular).
- `specialties`: ManyToManyField a `technical_services.ServiceCategory`,
  **`related_name='technician_profiles'`** (plural, no `'technicians'` como decia la version
  anterior de este doc — ese nombre esta literalmente comentado como "reservado" en el codigo).
  Para buscar tecnicos por categoria: `category.technician_profiles.all()`.
- `is_available`: BooleanField (default True).
- Se crea automaticamente via signal `post_save` en `UserProfile` cuando `user_type` esta en
  `SERVICE_PROVIDER_TYPES` (TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR) — **[CORREGIDO
  2026-07-23]** el nombre del modelo (`TechnicianProfile`) sugiere que solo aplica a TECHNICIAN,
  pero el signal real (`accounts/models.py:400-409`, comentario explicito en el codigo) se
  generaliza a los 4 tipos service-provider, no solo TECHNICIAN.

### Clases de permiso (fuente de verdad)

Archivo: `users/api/permissions.py`

| Clase | Condicion de acceso |
|-------|---------------------|
| `IsAdminUser` | `is_staff AND is_superuser` |
| `IsAuthenticatedActiveUser` (alias `IsCustomerUser`) | cualquier usuario activo autenticado |
| `IsOwnerOrAdmin` | objeto propio o admin (object-level) |
| `IsAdminOrReadOnly` | GET/HEAD/OPTIONS libres; escritura solo admin |
| `IsDispatcherUser` / `IsDispatcherOrAdmin` | `DispatcherProfile` activo (app `operations`) |
| `IsOperationalUser` | TECHNICIAN/PROFESSIONAL/SPECIALIST/TRANSPORTER/CONTRACTOR o dispatcher |
| `IsBuyerOrAdmin` | `UserProfile.user_type` en `BUYER_TYPES` (`CUSTOMER, TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR`) + admin — usar en `cart`, `orders`, `renting` |
| `IsServiceProviderUser` / `IsServiceProviderOrAdmin` | `user_type` en `SERVICE_PROVIDER_TYPES` (`TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR`) — usar en CV/skills/agenda |
| `IsTransporterUser` | solo `TRANSPORTER` |
| `IsAccountantUser` | solo `ACCOUNTANT` |

**Importacion correcta en ViewSets de negocio (nunca `rest_framework.permissions.IsAdminUser`):**

```python
from users.api.permissions import IsAdminUser
```

### Gap conocido — CERRADO 2026-07-03

Se encontraron y corrigieron **inconsistencias reales** de `permission_classes` no declarado en
varios ViewSets de solo-lectura:

| App | ViewSet | Antes | Corregido a |
|---|---|---|---|
| `renting` | `RentingCategoryViewSet`, `RentingBrandViewSet`, `RentalLaborViewSet` | Sin declarar -> `IsAuthenticated` (default) | `permissions.AllowAny` explicito — ademas las dos primeras usaban selectores "_for_admin" (exponian items inactivos); ahora usan `list_categories()`/`list_rental_labor()` (solo `is_active=True`) |
| `marketing` | `MarketingCampaignViewSet`, `AgentRunViewSet`, `DashboardViewSet` | Sin declarar -> `IsAuthenticated` (default) | `IsAdminUser` (de `users.api.permissions`) |
| `marketing` | `FlashOfferViewSet` | Sin declarar -> `IsAuthenticated` (default) | `permissions.AllowAny` (su selector ya filtraba `is_active=True`, es vitrina publica) |

Cubierto por `renting/tests.py` y `marketing/tests.py` (no existian antes de esta correccion).

### SSoT de identidad + arquitectura de perfiles (2026-07-06 a 2026-07-09) — no capturado en v7

Dos piezas nuevas que cambian como el resto del proyecto debe leer/escribir `user_type`:

1. **`ProfileResolver`/`ProfileRegistry`** (`accounts/services/profile_resolver.py`,
   `profile_registry.py`) — punto unico de acceso a `user.profile`/`user.technician_profile`/
   `user.dispatcher_profile`. Prohibido `getattr(user, 'profile', None)` directo en codigo nuevo;
   usar `ProfileResolver.get_profile()`/`get_type()`/`has_type()`/`resolve()` (lanza
   `MissingRequiredProfile`/`ProfileMismatchError` cuando corresponde). `BUYER_TYPES`/
   `SERVICE_PROVIDER_TYPES`/`OPERATIONAL_TYPES`/`CONTRACTOR_ASSIGNABLE_TYPES` en
   `profile_registry.py` son la unica fuente de verdad de que tipos pertenecen a que grupo de
   dominio — nunca redefinir listas de tipos sueltas en otra app. `VendorProfile` se elimino
   (codigo muerto, ningun endpoint lo poblaba).
2. **Registro siempre CUSTOMER + upgrade via KYC** — todo registro publico
   (`AccountCommands.register_user()`/`create_from_verified_payload()`) crea SIEMPRE
   `UserProfile.CUSTOMER` con acceso instantaneo (`KycCommands.bootstrap_approved`, sin esperar
   revision admin). Convertirse en TECHNICIAN/PROFESSIONAL/SPECIALIST/CONTRACTOR es un **upgrade
   posterior**, disparado solo desde el dashboard autenticado
   (`ContractorOnboardingWizard.vue` → `POST auth/request-upgrade/` → app `kyc`, ver seccion
   dedicada abajo). **Endurecido 2026-07-09:** ni siquiera un admin puede crear un perfil
   especializado directamente desde `/panel/usuarios` — `UserAdminCreateSerializer` ya no expone
   `user_type` (siempre CUSTOMER); el unico camino para que un usuario cambie de tipo es
   `KycCommands._apply_requested_user_type()` al aprobar un upgrade. TRANSPORTER sigue siendo un
   sistema separado (`operations.DispatcherProfile`, gestionado en `/panel/despachadores`, con
   test de regresion propio que garantiza que nunca toca `UserProfile.user_type`) — no participa
   de este flujo de upgrade.

---

## Service Layer

Todas las apps implementan el mismo patron DDD:

```
app/
  services/
    __init__.py       # re-exporta Commands y Selectors
    commands.py       # operaciones de escritura (@transaction.atomic)
    selectors.py      # queries de lectura (sin efectos secundarios)
    [extra].py        # pricing_service, calculator, pdf_service, summary, kardex

dashboard/
  services/
    admin_orchestrators.py  # Orchestrators del BFF — delegan a Commands/Selectors
```

### Reglas

- **Commands:** toda escritura en un Command estatico. Usan `@transaction.atomic`.
  WebSocket notifications via `transaction.on_commit(lambda: ...)` — hoy centralizadas en
  `notifications.services.commands.NotificationCommands.dispatch_notification()`, no `ws_notify`
  directo (ver app `notifications`).
- **Selectors:** toda lectura en un Selector estatico. Sin efectos secundarios.
- **Los ViewSets no tocan ORM directamente** — solo llaman Commands y Selectors.
- **Soft-delete obligatorio:** `is_active=False` + `is_deleted=True` (ambos campos, cuando el
  modelo tiene ambos). Los selectores de admin filtran `is_deleted=False`. Nunca DELETE fisico.

> **Leccion de la auditoria 2026-07-03:** se encontraron 10 casos donde un refactor "para
> desacoplar de `inventory` via un signal" quedo a medias — el signal nunca se construyo, y
> quedaron funciones stubeadas (`return True`/`pass`) o imports comentados con la marca
> `# INVENTORY_REMOVED: ... -> usar /api/v1/inventory/ o signal` mientras el codigo que los
> consumia seguia intacto. Esto rompio: descuento de inventario real en pagos (Wompi/Nequi/COD),
> validacion de stock en `cart`, confirmacion de ordenes COD en `orders`, estadisticas de
> `shop.services.summary`, y varios archivos `tests.py` (crasheaban con `NameError` antes de
> correr). **Regla derivada:** si aparece un comentario `INVENTORY_REMOVED` o similar prometiendo
> un reemplazo, verificar que el reemplazo exista antes de asumir que el codigo esta bien.

---

## Modelo base compartido

```python
# ecommerce/base_models.py
class SintelBaseModel(models.Model):
    uuid       = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    class Meta:
        abstract = True
```

Todos los modelos de negocio heredan de `SintelBaseModel`. `is_active` es un campo aparte que cada
modelo declara por su cuenta cuando aplica (no viene de `SintelBaseModel`).

> **[CORREGIDO 2026-07-03 — Fase 6, auditoria de base de datos]** `SintelBaseModel.Meta.indexes`
> declaraba `models.Index(fields=['uuid'])` y `models.Index(fields=['-created_at'])` **ademas**
> de `db_index=True` en esos mismos campos. Verificado con `sqlmigrate` contra Postgres real: esto
> generaba **dos indices fisicos redundantes por tabla** en absolutamente todas las tablas del
> proyecto (el de `uuid` es 100% redundante con el indice que ya crea `unique=True`; el de
> `created_at` descendente es redundante en Postgres porque un B-tree se recorre en ambas
> direcciones). Se elimino `Meta.indexes` del modelo base. Se generaron 8 migraciones
> (`cart`, `marketing`, `orders`, `quotes`, `renting`, `shop`, `technical_services`, `users` —
> las demas apps no tenian modelos con esos indices duplicados todavia) con **unicamente
> operaciones `RemoveIndex`**, aplicadas y verificadas contra la BD real (`pg_indexes`) y contra
> la suite de tests completa (102+5 tests, sin regresiones nuevas). Efecto: menos overhead de
> escritura (INSERT/UPDATE) y de espacio en disco en cada tabla del sistema, sin cambio de
> comportamiento de consultas.

---

## dashboard — BFF Administrativo (patron clave)

`dashboard` es un Backend for Frontend centralizado. El panel admin SPA consume
exclusivamente `/api/v1/dashboard/`.

```
Vue SPA (/panel/*)
    |
    +-- /api/v1/dashboard/*  ->  dashboard/api/views.py  (ViewSets)
                                        |
                                dashboard/services/admin_orchestrators.py
                                        |
                        Commands + Selectors de cada app (shop, renting, orders, ...)
```

### Orchestrators (verificado 2026-07-03 contra los imports reales de `dashboard/api/views.py`)

| Orchestrator | Delegacion |
|-------------|-----------|
| `AdminMetricsOrchestrator` | Metricas consolidadas para `AdminMetricsView` |
| `UserAdminOrchestrator` | `UserSelector`, `AccountCommands` |
| `ShopAdminOrchestrator` | `ProductSelector/Commands`, `CategorySelector/Commands`, `BrandSelector/Commands`, `TaxSelector/Commands` |
| `ServiceAdminOrchestrator` | `ServiceSelector/Commands`, `ServiceCategoryCommands` |
| `RentingAdminOrchestrator` | `RentingSelector`, `EquipmentCommands`, `EquipmentVariantCommands`, `RentingBrandCommands`, `RentingCategoryCommands` |
| `QuotationAdminOrchestrator` | `QuotationSelector`, `QuotationCommands` |
| `QuoteTemplateAdminOrchestrator` | Comandos del constructor de plantillas/cuestionarios CPQ |
| `OrderAdminOrchestrator` | `OrderSelector` |
| `MarketingAdminOrchestrator` | `MarketingSelector` |
| `SupportAdminOrchestrator` | `ChatSelector`/`ChatCommands` (panel `/panel/soporte`) |

> Ver ahora `dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` (creado 2026-07-03) para
> el inventario completo de las 34 ViewSets reales — esta seccion se mantiene como resumen rapido.

> **[CORREGIDO 2026-07-03] `InventoryAdminOrchestrator` NO EXISTE.** La version anterior de este
> documento lo listaba con rutas `/api/v1/dashboard/inventory/...`. Se verifico que fue eliminado
> por completo (sin ninguna referencia colgante en todo el proyecto) y que la administracion de
> inventario se **consolido correctamente** en `/api/v1/inventory/stock-records/...`
> (`inventory/api/views.py`, `StockRecordViewSet`). Confirmado con una prueba real: `GET/POST
> /api/v1/dashboard/inventory/...` devuelve 404. No reintroducir esta ruta — usar siempre
> `/api/v1/inventory/`.

### Endpoints del dashboard (corregidos)

Todos requieren `IsAuthenticated + IsAdminUser` (de `users.api.permissions`).

| Endpoint | ViewSet |
|----------|---------|
| `GET /api/v1/dashboard/metrics/` | `AdminMetricsView` — ventas, ordenes, clientes, productos |
| ~~`/api/v1/dashboard/users/`~~ | **[CORREGIDO 2026-07-23] `AdminUserViewSet` NO EXISTE** — eliminado 2026-07-05 (comentario explicito en `dashboard/api/views.py:140-141`: el frontend nunca lo llamaba y ya habia divergido). Versiones anteriores de este documento lo listaban por error. Gestion de usuarios vive solo en `/api/v1/users/` (`users.api.views.UserViewSet`) |
| `/api/v1/dashboard/products/` | `AdminProductViewSet` + actions: `variants/`, `variants/create`, `variants/<pk>` |
| `/api/v1/dashboard/categories/` | `AdminCategoryViewSet` — acepta multipart (image upload) |
| `/api/v1/dashboard/brands/` | `AdminBrandViewSet` — acepta multipart (logo upload) |
| `/api/v1/dashboard/taxes/` | `AdminTaxViewSet` |
| `/api/v1/dashboard/orders/` | `AdminOrderViewSet` |
| ~~`/api/v1/dashboard/inventory/`~~ | **Eliminado — usar `/api/v1/inventory/stock-records/`** |
| `/api/v1/dashboard/equipment/` | `AdminEquipmentViewSet` + actions: `variants/`, `variants/create`, `variants/<pk>` |
| `/api/v1/dashboard/renting-categories/` | `AdminRentingCategoryViewSet` |
| `/api/v1/dashboard/renting-brands/` | `AdminRentingBrandViewSet` |
| `/api/v1/dashboard/rental-labor/` | `AdminRentalLaborViewSet` |
| `/api/v1/dashboard/quotations/` | `AdminQuotationViewSet` |
| `/api/v1/dashboard/services/` | `AdminTechnicalServiceViewSet` |
| `/api/v1/dashboard/service-categories/` | `AdminServiceCategoryViewSet` |
| `/api/v1/dashboard/marketing/summary` | `AdminMarketingViewSet` |
| `/api/v1/dashboard/home-config/` (u similar) | Configuracion de landing/home — ver app `core` |
| `/api/v1/dashboard/operations/` | Panel admin de tickets/asignaciones — ver app `operations` |

### Serializers

`dashboard/api/serializers.py` re-exporta los serializers de cada app.
No define serializers propios — es un punto de entrada unico.

---

## Rutas API raiz (`ecommerce/urls.py`) — reescrito 2026-07-20 (la version 2026-07-09 ya estaba
desactualizada: le faltaban las 3 rutas de `admin-auth` de recuperacion de clave, las 2 de
`internal/ai*`, `organization/` completa y `security` — verificado leyendo el archivo real)

```python
path('api/v1/health/',        health_check),
path('admin/',                 admin.site.urls),                 # Django Admin, no confundir con /panel/*
path('api/schema/',            SpectacularAPIView...),            # OpenAPI, solo IsAdminUser
path('api/docs/',              SpectacularSwaggerView...),        # Swagger UI, solo IsAdminUser

# Admin auth — ruta aislada, nunca fusionar con api/v1/auth/ (login de CLIENTE)
path('api/v1/admin-auth/login/',                     AdminLoginView.as_view()),
path('api/v1/admin-auth/forgot-password-request/',   AdminForgotPasswordRequestView.as_view()),  # <- nuevo, rediseno Auth 2026-07-17
path('api/v1/admin-auth/forgot-password-verify/',    AdminForgotPasswordVerifyView.as_view()),    # <- nuevo
path('api/v1/admin-auth/reset-password/',            AdminResetPasswordView.as_view()),           # <- nuevo

# Internal — SOLO consumido por el AI Engine via red Docker, nunca por el frontend
path('api/v1/internal/ai-context/', AiContextView.as_view()),      # <- nuevo, AI Core Fase 1 (2026-07-16)
path('api/v1/internal/ai/',   include('ecommerce.internal_ai_urls')),  # <- nuevo, AI Core Fase 2+ (Tools de lectura)

path('api/v1/auth/',          include('accounts.urls')),
path('api/v1/auth/',          include('kyc.api.urls')),        # <- comparte prefijo con accounts
path('api/v1/users/',         include('users.urls')),
path('api/v1/dashboard/',     include('dashboard.api.urls')),
path('api/v1/shop/',          include('shop.urls')),
path('api/v1/cart/',          include('cart.urls')),
path('api/v1/orders/',        include('orders.urls')),
path('api/v1/payment/',       include('payment.urls')),       # <- NO 'wompi'
path('api/v1/inventory/',     include('inventory.urls')),
path('api/v1/services/',      include('technical_services.urls')),
path('api/v1/service-operations/', include('technical_services.api.operation_urls')),
path('api/v1/services/',      include('technical_services.api.availability_urls')),  # <- segundo include, no listado antes
path('api/v1/quotes/',        include('quotes.urls')),
path('api/v1/marketing/',     include('marketing.urls')),
path('api/v1/renting/',       include('renting.urls')),        # incluye 'operations/' desde 2026-07-07
path('api/v1/core/',          include('core.urls')),
path('api/v1/notifications/', include('notifications.api.urls')),
path('api/v1/operations/',    include('operations.api.urls')),
path('api/v1/organization/',  include('organization.api.urls')),  # <- nuevo, app creada 2026-07-12
path('api/v1/support/',       include('support.api.urls')),       # <- CORREGIDO 2026-07-23: SI existe (ver abajo)
path('api/v1/',               include('security.api.urls')),      # <- nuevo, monta SIN prefijo propio: resuelve a /api/v1/security/health/
```

**[CORREGIDO 2026-07-23] `path('api/v1/support/', ...)` SI existe** (`ecommerce/urls.py:68`) —
las versiones anteriores de este documento (v9 y previas) afirmaban explicitamente lo contrario
("no existe"/"support es 100% WebSocket") en este bloque y en la seccion `support` de abajo. Es
un solo endpoint real, `POST /api/v1/support/chats/<uuid>/rate/` (calificacion CSAT) — el resto
de la interaccion de `support` sigue siendo 100% WebSocket. Ver seccion `support` para el detalle.
**No existe `path('api/v1/wompi/', ...)`** — cualquier referencia a esa ruta en documentacion vieja
o memoria es incorrecta.
**`kyc.api.urls` comparte el prefijo `api/v1/auth/`** con `accounts.urls` (no tiene prefijo propio
`api/v1/kyc/`) — ej. `POST /api/v1/auth/request-upgrade/`, `GET /api/v1/auth/verification/`.
**`security.api.urls` se monta en la raiz `api/v1/`, sin prefijo `security/` en el `include()`**
— el prefijo real (`api/v1/security/health/`) viene del propio `path()` dentro de
`security/api/urls.py`, no de como se incluye en `ecommerce/urls.py`. Si se agrega otra ruta a
esa app, debe llevar su propio prefijo `security/` explicito (el `include()` raiz no lo aporta).
**Fulfillment de productos fisicos ("Shop Operations") NO tiene prefijo propio** — vive como
acciones nuevas dentro de `OrderViewSet` bajo `/api/v1/orders/orders/` (`operations/`,
`operations-dashboard/`, `pack/`, `assign-dispatcher/`, `schedule-dispatch/`, etc. — ver seccion
`orders` abajo).
**El AI Engine (`ai_engine/`, FastAPI puerto 8100) es un servicio Docker separado, NO parte de
este `urls.py`** — sus rutas (`/chat`, `/api/v1/ai/context`, `/generate`, etc.) viven en su
propio proceso. **[CORREGIDO 2026-08-17]** el lado Django del puente son los `path()` de arriba
(`ai-context/` + el `include()` de `internal_ai/`), pero ese `include()` expande a **31
endpoints reales** (`ecommerce/internal_ai_urls.py`), no un par de rutas sueltas — ver seccion
`ai_engine` mas abajo para el detalle completo del flujo.

---

## Apps y estado de implementacion

### accounts — Autenticacion

Archivo: `accounts/api/views.py`

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/auth/register/` | POST | AllowAny |
| `/api/v1/auth/login/` | POST | AllowAny |
| `/api/v1/auth/logout/` | POST | IsAuthenticated |
| `/api/v1/auth/profile/` | GET, PATCH | IsAuthenticated |
| `/api/v1/auth/change-password/` | POST | IsAuthenticated |
| `/api/v1/auth/register-request/` | POST | AllowAny |
| `/api/v1/auth/register-verify/` | POST | AllowAny |
| `/api/v1/auth/register-resend/` | POST | AllowAny — **agregado 2026-07-23**, no estaba en la tabla |
| `/api/v1/auth/verify-email-confirm/` | POST | AllowAny — **agregado 2026-07-23** |
| `/api/v1/auth/forgot-password-request/` | POST | AllowAny — **agregado 2026-07-23**, recuperacion de clave de CLIENTE (no confundir con `admin-auth/forgot-password-*`) |
| `/api/v1/auth/forgot-password-verify/` | POST | AllowAny — **agregado 2026-07-23** |
| `/api/v1/auth/forgot-password-reset/` | POST | AllowAny — **agregado 2026-07-23** |

Services: `AccountCommands`, `AccountSelector`

**[NUEVO 2026-07-17, no releido a fondo esta pasada] Rediseno de Auth (5 fases).** Login/
Registro/Recuperar-contrasena del cliente se movieron a `CustomerAuthLayout.vue` (pantalla
completa, sin navbar/footer de marketing) en `/login` y `/register`. El login de ADMIN sigue
100% separado (`/panel/login` -> `AdminLoginView`/`admin-auth/login/`, nunca fusionar). Nuevo:
`GatedTokenObtainPairSerializer` (`accounts/api/views.py`) — hace que la ruta paralela
`POST /api/v1/auth/token/` (SimpleJWT estandar) tambien pase por el mismo gate de KYC que
`AccountCommands.authenticate_user()`, y rechaza explicitamente cuentas `is_staff`/`is_superuser`
("Esta cuenta debe iniciar sesion desde el panel de administracion") — sin este gate, esa ruta
emitia tokens sin pasar por ninguna de las 2 validaciones. Un usuario recien creado por
`User.objects.create()` fuera del flujo normal de registro (ej. en un script de datos de prueba)
NO puede loguearse hasta que se le llame `kyc.services.commands.KycCommands.bootstrap_approved(user)`
— el registro normal ya lo hace automaticamente, esto solo importa para scripts/seeds manuales.

**[NUEVO 2026-07-13, no releido a fondo esta pasada] Aislamiento de dominio del panel (ADR-001).**
`panel.sintel.net.co` (admin) y `sintel.net.co`/`api.sintel.net.co` (cliente) son 2 vhosts nginx
separados que comparten directivas via `nginx-common.conf` (Fase 2 del ADR) — YA DESPLEGADO en
produccion. No confundir con el rediseno de Auth (frentes distintos, misma semana de trabajo).

---

### kyc — Verificacion de identidad — app nueva, no listada antes (2026-07-06)

Archivo: `kyc/api/views.py` — montada bajo el mismo prefijo `/api/v1/auth/` que `accounts`
(`path('api/v1/auth/', include('kyc.api.urls'))`), no tiene prefijo propio.

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/auth/verification/` | GET | IsAuthenticatedActiveUser — estado propio |
| `/api/v1/auth/upload-document/` | POST | IsAuthenticatedActiveUser |
| `/api/v1/auth/submit-for-review/` | POST | IsAuthenticatedActiveUser |
| `/api/v1/auth/request-upgrade/` | POST | IsAuthenticatedActiveUser — unico disparador de un cambio de `user_type` |
| `/api/v1/auth/documents/` | GET, DELETE | IsAuthenticatedActiveUser — propios |
| `/api/v1/auth/documents/<uuid>/download/` | GET | dueno o IsAdminUser (storage privado) |
| `/api/v1/auth/admin/verifications/` | GET | IsAdminUser — cola de revision (`/panel/validaciones`) |
| `/api/v1/auth/admin/verifications/<uuid>/` | GET, actions `approve/`, `reject/`, `request-info/`, `force-approve/`, `block/`, `review-document/` | IsAdminUser |
| `/api/v1/auth/admin/verifications/metrics/` | GET | IsAdminUser — KPIs para `/panel/validaciones` |

Modelos: `UserVerification` (OneToOne con `User`, reutilizada toda la vida del usuario — para el
acceso CUSTOMER inicial y para cualquier upgrade posterior), `VerificationDocument`,
`VerificationEvent` (timeline append-only), `ConsentRecord` (Habeas Data, Ley 1581/2012).

Services: `KycCommands` (`bootstrap_approved`, `request_upgrade`, `upload_document`,
`submit_for_review`, `approve`, `force_approve`, `reject`, `request_more_info`, `block`,
`review_document`), `KycSelector` (`get_own_verification`, `list_queue`, `get_admin_metrics`).

**Maquina de estados:** `PENDING -> UNDER_REVIEW -> APPROVED | REJECTED`, mas `BLOCKED` (terminal)
y `EXPIRED` (reservado, nada lo dispara aun). `approve()` exige que todos los documentos
requeridos para el `requested_user_type` esten `APPROVED` individualmente.

**Motor de requisitos por tipo:** `kyc/services/config.py::REQUIRED_DOC_TYPES_BY_TYPE` — dict
`user_type -> [doc_type]`, una entrada por cada `SERVICE_PROVIDER_TYPES` (hoy los 4 tipos
comparten los mismos 5 documentos; agregar un tipo nuevo = sumar una entrada, no reescribir
`KycCommands`).

**Storage privado — critico:** `VerificationDocument.file` usa `PrivateKycStorage`, fuera de
`MEDIA_ROOT` (`KYC_PRIVATE_STORAGE_ROOT`), `base_url=None` — el unico acceso posible es el
endpoint `download/` autenticado. Nunca exponer esa ruta en nginx.

**Gate de login:** `AccountCommands._assert_kyc_approved(user)` bloquea solo si
`status == BLOCKED`, o si `first_approved_at is None` (nunca fue aprobado) — permite que un
CUSTOMER con un upgrade `PENDING`/`UNDER_REVIEW` en curso siga comprando sin perder acceso.

---

### users — Gestion de usuarios (admin)

Archivo: `users/api/views.py`

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/users/` | GET, POST | IsAuthenticated + IsAdminUser |
| `/api/v1/users/<uuid>/` | GET, PATCH, DELETE | IsAuthenticated + IsAdminUser |
| `/api/v1/users/<uuid>/erase/`, `.../reset-password/`, `.../resend-verification/`, `.../groups/`, `/api/v1/users/groups-catalog/`, `/api/v1/users/<uuid>/audit-log/` | — | admin — **agregado 2026-07-23**, 6 acciones reales de `UserViewSet` que no estaban en la tabla |

**SSoT de identidad (2026-07-09):** `UserAdminCreateSerializer`/`UserAdminUpdateSerializer`
(`users/api/serializers.py`) ya NO exponen `user_type` — todo usuario creado desde `/panel/usuarios`
nace CUSTOMER (`AccountCommands.register_user()` defaultea a `UserProfile.CUSTOMER`); el tipo de un
usuario existente solo cambia al aprobar un upgrade KYC (`KycCommands._apply_requested_user_type`),
nunca desde este endpoint.

Services: `UserCommands`, `UserSelector`

---

### shop — Catalogo de productos

Archivo: `shop/api/views.py`

| ViewSet | Endpoint base | Escritura |
|---------|--------------|-----------|
| `ProductViewSet` | `/api/v1/shop/products/` | Solo lectura publica |
| `CategoryViewSet` | `/api/v1/shop/categories/` | Solo lectura publica |
| `BrandViewSet` | `/api/v1/shop/brands/` | Solo lectura publica |
| `TaxViewSet` | `/api/v1/shop/taxes/` | Solo lectura publica |

Escritura SIEMPRE via `dashboard/products/`, `dashboard/categories/`, etc.

Services: `ProductCommands`, `CategoryCommands`, `BrandCommands`, `TaxCommands`,
`ProductSelector`, `CategorySelector`, `BrandSelector`, `PricingService`, `ShopSummaryProvider`

Notas:
- `create_product()` crea un `ProductVariant` por defecto en la misma transaccion; el SKU se
  **auto-genera** (`_generate_variant_sku()`), nunca se acepta SKU manual del usuario (verificado
  2026-07-03 al descartar un cambio incorrecto que habria reintroducido SKU manual).
- `stock` en `ProductVariant` es cache — fuente de verdad es `StockRecord` (inventory).
- `ShopSummaryProvider.get_summary()` (consumido por `marketing`) tuvo una regresion corregida el
  2026-07-03: devolvia `in_stock/out_of_stock/total_stock_units` hardcodeados en 0 — restaurado
  para calcularlos desde `StockRecord` real.
- Soft-delete: `is_active=False` + `is_deleted=True`.

**Corregido 2026-07-03 (Fase 6, auditoria de BD):**
- `Product.is_active`/`is_featured` no tenian `db_index=True` pese a filtrarse en los selectores
  publicos de catalogo. Agregado (migracion `shop/0008`).
- `ProductReview` prevenia duplicados (`user`+`product`) solo a nivel de aplicacion
  (`ProductReviewSerializer.validate()`); una condicion de carrera podia dejar reseñas
  duplicadas. Agregado `unique_together = ('user', 'product')` en BD (verificado que no habia
  duplicados existentes antes de migrar), y `ProductViewSet.review()` ahora atrapa
  `IntegrityError` -> 400 limpio en vez de dejar escalar un 500 si la carrera llegara a ocurrir.
  Cubierto por `shop/tests.py` (no existia antes).

---

### inventory — Stock y movimientos

Archivo: `inventory/api/views.py` — `StockRecordViewSet`

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/inventory/stock-records/` | GET | IsAdminUser |
| `/api/v1/inventory/stock-records/<uuid>/movements/` | GET | IsAdminUser — **[CORREGIDO 2026-07-23]** antes decia `.../transactions/`, el `url_path` real es `movements` (`inventory/api/views.py:103`) |
| `/api/v1/inventory/stock-records/<uuid>/adjust-stock/` | POST | IsAdminUser |
| `/api/v1/inventory/transactions/` | GET | IsAdminUser — **agregado 2026-07-23**, ruta top-level separada (`InventoryTransactionViewSet`, listado global sin filtrar por stock-record) — no confundir con `movements/`, que es el historial de UN stock-record especifico |

Services: `InventoryCommands` (`register_entry`, `register_exit`), `InventorySelector`
(`get_current_stock`, `get_stock_for_variant`), `InventoryKardex`.

**Esta es la unica fuente de verdad de stock del proyecto.** Todo descuento post-pago pasa por
`payment.shared.commands._deduct_inventory_for_order()`, que a su vez llama
`InventoryCommands.register_exit()` — nunca se debe llamar `register_exit()` directamente desde
otra app fuera de ese punto (ver app `payment`).

---

### cart — Carrito de compras

Archivo: `cart/api/views.py` — `CartViewSet` + `WishlistViewSet`, **ambos con permiso real
`IsBuyerOrAdmin`** — **[CORREGIDO 2026-07-23]** versiones anteriores de este documento decian
que `WishlistViewSet` usaba `IsAuthenticatedActiveUser`; el codigo real (`cart/api/views.py:140,
147`) usa el mismo `IsBuyerOrAdmin` que `CartViewSet` (import identico de
`users.api.permissions`).

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/cart/` | GET | IsBuyerOrAdmin |
| `/api/v1/cart/add_item/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/update_item/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/clear/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/remove-item/<uuid>/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/checkout/` | POST | IsBuyerOrAdmin — preview de checkout, precios congelados + verificacion de stock |
| `/api/v1/cart/wishlist/` | GET, POST | IsBuyerOrAdmin |
| `/api/v1/cart/wishlist/<uuid>/` | DELETE (soft) | IsBuyerOrAdmin |

Services: `CartCommands`, `CartSelector`

**Fix 2026-07-03:** `_check_availability()` y `checkout_cart()` habian perdido la validacion real
de stock (retornaban `9999` fijo) — restaurado via `InventorySelector.get_current_stock()`.

**Corregido 2026-07-03 (Fase 6, auditoria de BD):** "un carrito por usuario" y "un CartItem por
(cart, variant)/(cart, service_variant)" solo se garantizaban por convencion de aplicacion
(`get_or_create()`), vulnerables a condicion de carrera. Se agrego `unique=True` en `Cart.user` y
`CheckConstraint` + 2 `UniqueConstraint` parciales en `CartItem` (migration `cart/0005_...`).
`CartCommands.add_item()` ahora captura el `IntegrityError` resultante y fusiona la cantidad en
vez de fallar. Ver `[[project_db_audit_duplicate_indexes]]`.

---

### orders — Pedidos y fulfillment

Archivo: `orders/api/views.py`, `orders/api/service_orders.py`, `orders/services/fulfillment/`

| ViewSet | Endpoint | Permiso |
|---------|----------|---------|
| `ShippingAddressViewSet` | `/api/v1/orders/addresses/` | IsBuyerOrAdmin |
| `OrderViewSet` | `/api/v1/orders/orders/` | IsBuyerOrAdmin |
| `OrderViewSet.create_from_cart` | `POST /api/v1/orders/orders/create_from_cart/` | IsBuyerOrAdmin |
| `OrderViewSet` (fulfillment) | `/{uuid}/prepare/`, `/pack/`, `/assign-dispatch-center/`, `/assign-carrier/`, `/assign-driver/`, `/dispatch/`, `/in-transit/`, `/deliver/`, `/timeline/`, `/tracking/` | admin (fulfillment) |
| `ServiceOrderViewSet` | `/api/v1/orders/service-orders/` (create/list/retrieve `IsAuthenticated`; `assign-technician/`, `auto-assign/` `IsAdminUser`; `confirm-cod/` owner) | mixto — ver `technical_services` |

Vista admin de ordenes: `GET /api/v1/dashboard/orders/` (via dashboard BFF).

Services: `OrderCommands.create_from_cart()`, `OrderSelector`, `FulfillmentCommands`
(`start_preparation`, `complete_packing`, etc. — motor de estados granular con modelo `Shipment`).

**Modelo de estados real (no el modelo viejo `pending/processing/paid/shipped/delivered`):**
`STATUS_CREATED`, `STATUS_PENDING_PAYMENT`, `STATUS_PAID`, `STATUS_PREPARING`,
`STATUS_READY_FOR_DISPATCH`, `STATUS_ASSIGNED`, `STATUS_PICKED_UP`, `STATUS_IN_TRANSIT`,
`STATUS_OUT_FOR_DELIVERY`, `STATUS_DELIVERED`, `STATUS_COMPLETED`, `STATUS_CANCELLED`,
`STATUS_RETURN_REQUESTED`, `STATUS_RETURNED`, `STATUS_FAILED_DELIVERY`, `STATUS_LOST`.
`'pending'`/`'processing'` quedan solo como choices legacy — `create_from_cart()` ya no los usa.

**Bug critico corregido 2026-07-03 (checkout COD completo):** `create_from_cart()` habia dejado de
llamar a `CodCommands.confirm_order()` para pagos COD — toda orden COD quedaba creada y atascada en
`STATUS_PENDING_PAYMENT` para siempre, sin `CodTransaction` ni descuento de inventario. Restaurado;
`CodCommands.confirm_order()` ahora tambien transiciona `order.status = STATUS_PAID` (mismo gate que
usan Wompi/Nequi). Ademas se encontraron y corrigieron **3 instancias** de un bug relacionado:
`WompiPaymentViewSet.initialize()`, `NequiPaymentViewSet.initialize()` y
`ServiceOrderViewSet.confirm_cod()` comparaban `order.status` contra el string legacy `'pending'` en
vez de `Order.STATUS_PENDING_PAYMENT` — rechazaban con 400 toda orden recien creada. Ver
`orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md` para el detalle completo y los tests de
regresion agregados.

**Bug de rendimiento corregido 2026-07-03 (Fase 6, auditoria de BD):** `OrderSelector.list_for_user()`
y `list_all_for_admin()` (usadas por `OrderViewSet.list()` **y** `.retrieve()`, ya que el ViewSet no
sobreescribe `get_object()`) no traian `select_related`/`prefetch_related` para las relaciones que
`OrderSerializer` siempre serializa (`items`, `shipping_address`, `shipment` +
`shipment.dispatch_center/carrier/driver`). Ademas usaban un `.only(*LIST_FIELDS)` que ni siquiera
cubria todos los campos que el serializer necesita (`payment_method`, `discount_amount`,
`tracking_number`, `shipping_address_id` no estaban incluidos), causando recargas de campos
diferidos por cada orden. **Medido empiricamente:** listar 2 ordenes con item+shipment+carrier
completos tomaba **19 queries**, escalando linealmente con la cantidad de ordenes. Corregido:
`OrderSelector` ahora usa `select_related(...)` + `prefetch_related('items')` sin `.only()`
parcial — **3 queries constantes** sin importar cuantas ordenes se listen. Cubierto por
`orders.tests.OrderFulfillmentAPITestCase.test_list_orders_has_no_n_plus_1`
(`assertNumQueries(3)` — falla si alguien reintroduce el N+1). `OrderSelector.DETAIL_FIELDS` (dead
code, nunca se uso) se elimino en el mismo cambio.

**Indice agregado:** `Order.status` no tenia `db_index=True` pese a filtrarse constantemente
(metricas del dashboard, `ShopSummaryProvider`, etc.) — agregado.

### "Shop Operations" — fulfillment logistico de productos fisicos (2026-07-09, nuevo)

Evolucion de la logistica de pedidos de producto (picking/packing/despacho/entrega),
implementada **extendiendo** `orders.Shipment` + `orders/services/fulfillment/` (que ya existia
con el FSM base) en vez de crear un modelo nuevo — la auditoria previa a implementar encontro que
~90% de lo pedido ya estaba construido, solo faltaba UI funcional, notificaciones y creacion
automatica.

- **`Shipment` extendido:** nuevos campos `assigned_dispatcher` (FK a `operations.DispatcherProfile`
  — reusa el mismo pool de transportistas que Renting, gestionado en `/panel/despachadores`, en vez
  de duplicar con el `driver`/`carrier` legado sin FK a `User`), `responsible`, `shipping_method`
  (7 opciones), `dispatch_scheduled_at`, `route`, campos de empaque
  (`package_type/weight/volume/dimensions`), `evidence_photos`, `delivery_signature`,
  `customer_confirmed_at`.
- **Creacion automatica:** `FulfillmentCommands.ensure_shipment_for_order()` se dispara desde
  `payment/shared/commands.py::confirm_order_payment` y `payment/cod/services/commands.py::CodCommands.confirm_order`
  — el mismo punto donde ya se descuenta inventario. Solo para ordenes con al menos un item de
  producto fisico. El inventario se descuenta **una sola vez**, al pago; el despacho
  (`FulfillmentCommands.dispatch()`) solo valida stock de solo lectura, nunca vuelve a descontar.
- **Notificaciones nuevas:** 7 plantillas (`shop_order_received`, `shop_preparing_order`,
  `shop_dispatch_assigned`, `shop_order_shipped`, `shop_delivery_scheduled`, `shop_order_delivered`,
  `shop_delivery_confirmed`) disparadas desde `ShipmentTimelineCommands.add_event()`.
- **Endpoints nuevos en `OrderViewSet`** (`/api/v1/orders/orders/{uuid}/...`): `assign-dispatcher/`,
  `schedule-dispatch/`, `out-for-delivery/`, `complete/`, `confirm-delivery/` (cliente confirma
  recepcion); mas `operations/` y `operations-dashboard/` (detail=False) para la bandeja
  administrativa.
- **Frontend:** `ShopOperationBoard.vue` en `/panel/productos/operaciones` (anidado en el grupo
  "Tienda" del sidebar, no un menu independiente); `ShipmentStatusBadge.vue`/`ShipmentTimeline.vue`
  nuevos; `CustomerOrdersView.vue` gano el timeline real del shipment (reemplazo un stepper
  generico que usaba claves inexistentes en `Order.STATUS_CHOICES`).
- **Bug real encontrado en E2E (no reportado por el usuario):** `AssignmentCommands.assign_dispatcher()`
  actualizaba `Order.status` pero no `Shipment.status` — el boton de "siguiente paso" nunca
  aparecia tras asignar transportista. Corregido.

Ver [[project_shop_operations_module]] en memoria para el detalle completo.

---

### payment — Pagos (Wompi online + COD + Nequi Push)

> **[CORREGIDO 2026-07-03] Esta app se llama `payment`, NUNCA `wompi`.** La version anterior de
> este documento (y varios otros documentos del proyecto) la describian con un nombre de app, rutas
> y variables de entorno que no correspondian al codigo real. Verificado exhaustivamente contra
> `payment/apps.py`, `ecommerce/urls.py`, `ecommerce/settings/base.py` y las llamadas reales del
> frontend (`CheckoutView.vue`, etc.).

> **[NUEVO 2026-07-13] Migracion a integracion API propia con Wompi (ADR-001, 10 fases completas).**
> El checkout de tarjeta (nueva o guardada) ya NO depende del Widget de Wompi para crear la
> transaccion -- el backend la crea de forma sincrona via un adaptador propio
> (`payment/online/wompi_client.py::WompiApiClient`), con un feature flag real de reversion
> instantanea, historial de auditoria (`TransactionEvent`), reconciliacion mejorada, panel admin con
> acciones reales, y pruebas E2E/carga permanentes. **PSE queda excluido a proposito** (sigue usando
> el Widget completo, requiere redireccion al banco). Detalle completo:
> [ARQUITECTURA_COMPLETA_PAYMENT.md](../../ecommerce_sintel/payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md)
> seccion 10, y el ADR + informes por fase en `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md` /
> `FASE{0..9}_*.md` — no se repite el detalle aqui a proposito, este documento es un resumen de alto
> nivel, no la fuente de verdad.

Archivo: `payment/online/api/views.py` — `WompiPaymentViewSet` (el widget de Wompi es un metodo
dentro de la app `payment`, no la app en si); `payment/nequi/api/views.py` — `NequiPaymentViewSet`;
`payment/cards/views.py` — `TokenizedCardViewSet`.

| Endpoint | Metodo | Permiso | Descripcion |
|----------|--------|---------|-------------|
| `/api/v1/payment/payments/initialize/` | POST | IsAuthenticated | Crea `Transaction` PENDING, calcula firma SHA256. Si el body trae `card_token`/`payment_source_id` (checkout con tarjeta, 2026-07-13), crea la transaccion TAMBIEN de forma sincrona en Wompi -- 403 si el feature flag lo tiene desactivado |
| `/api/v1/payment/payments/feature-flags/` | GET | AllowAny | Estado del kill-switch `card_api_flow_enabled` (2026-07-13) |
| `/api/v1/payment/payments/webhook/` | POST | AllowAny | Receptor de eventos Wompi (firma HMAC verificada) |
| `/api/v1/payment/payments/transaction-status/` | GET | IsAuthenticated + ownership | Detalle post-pago (`?tx=<uuid>`) |
| `/api/v1/payment/payments/confirmation/` | GET | IsAuthenticated + ownership | Resultado consolidado; si sigue PENDING, sincroniza en vivo contra la API de Wompi (`_sync_wompi_status`) |
| `/api/v1/payment/nequi/initialize/` | POST | IsAuthenticated | Push Nequi |
| `/api/v1/payment/nequi/status/` | GET | IsAuthenticated + ownership | Polling de estado |
| `/api/v1/payment/cards/` | GET, POST, DELETE, `set-default/` | IsAuthenticatedActiveUser | Tarjetas tokenizadas — alta ahora automatizada desde el frontend (`useCardTokenization.js`, 2026-07-13), ya no se pega el token a mano |
| `/api/v1/dashboard/payment-transactions/{uuid}/resync/`, `.../events/`, `.../feature-flags/` | POST/GET/PATCH | Admin | Panel de pagos con acciones reales (2026-07-13) — antes 100% de solo lectura |

**Variables de entorno reales (verificadas en `ecommerce/settings/base.py`):**

```env
WOMPI_PUBLIC_KEY=pub_test_...
WOMPI_PRIVATE_KEY=prv_test_...
WOMPI_INTEGRITY_SECRET=...      # NO "WOMPI_INTEGRITY_KEY"
WOMPI_EVENTS_SECRET=...         # NO "WOMPI_EVENTS_KEY"
WOMPI_ENVIRONMENT=test|prod
WOMPI_WIDGET_URL=https://checkout.wompi.co/widget.js
NEQUI_CLIENT_ID=...
NEQUI_CLIENT_SECRET=...
NEQUI_API_KEY=...
NEQUI_ENVIRONMENT=sandbox
```

**Integridad del checkout:**
`integrity_signature = SHA256(transaction_uuid + amount_in_cents + currency + WOMPI_INTEGRITY_SECRET)`.

**Verificacion de firma del webhook — YA IMPLEMENTADA (no es un pendiente):**
`_verify_wompi_event_signature()` en `payment/online/api/views.py`, algoritmo oficial de Wompi
(properties + timestamp + `WOMPI_EVENTS_SECRET`, comparacion timing-safe). Si `WOMPI_EVENTS_SECRET`
esta vacio, se permite pasar (modo desarrollo) — **debe configurarse en produccion**.

**Flujo de pago (3 metodos, Wompi con 2 sub-flujos desde 2026-07-13):**
1a. Wompi/Tarjeta (backend-directo, sub-metodo "Tarjeta" del checkout): `initialize/` con `card_token`
    -> `WompiApiClient` crea la transaccion sincrona en Wompi (sin abrir widget) -> `webhook/` (sigue
    siendo la unica fuente de verdad autoritativa) -> `PaymentCommands.confirm_payment()` ->
    `confirm_order_payment()` -> `Order.status = paid` + descuento inventario + notificacion.
1b. Wompi/PSE-Otros (sub-metodo "PSE / Otros", sin cambios de comportamiento): `initialize/` sin
    `card_token` -> widget completo -> `webhook/` -> mismo `confirm_order_payment()`.
2. Nequi: `nequi/initialize/` -> push al celular -> polling `nequi/status/` -> mismo `confirm_order_payment()` al aprobarse.
3. COD: descuento de inventario y confirmacion **inmediatos** dentro de `create_from_cart()`, via `CodCommands.confirm_order()` (bug de checkout corregido 2026-07-03, ver seccion `orders`).

**Corregido 2026-07-03 (Fase 6, auditoria de BD):**
1. `Transaction.status` gano `db_index=True` (sus hermanos `CodTransaction.status`/`NequiTransaction.status` ya lo tenian).
2. `Transaction` y `NequiTransaction` ganaron un `CheckConstraint` en BD que exige exactamente uno de `order`/`rental_request` establecido — antes solo era una convencion documentada, sin proteccion real.
3. `TokenizedCard` gano `UniqueConstraint(user, condition=is_default & ~is_deleted)` para garantizar en BD "una sola tarjeta default por usuario" (antes solo lo garantizaba `cards/views.py` con dos escrituras no atomicas). `create()`/`set_default()` ahora usan `transaction.atomic()` + capturan `IntegrityError` -> `409`.
4. **Bug de produccion inedito encontrado al testear lo anterior:** `TokenizedCardViewSet.destroy()` asignaba y guardaba un campo `is_active` que **no existe** en `TokenizedCard` -> `ValueError` (500) en toda llamada real a `DELETE /api/v1/payment/cards/{uuid}/`. El endpoint nunca funciono; no habia tests que lo cubrieran. Corregido. Migracion `payment/0007_...`. Ver `[[project_db_audit_duplicate_indexes]]` para el detalle completo.

**Bug critico corregido 2026-07-03:** `_deduct_inventory_for_order()` y `_has_sufficient_stock()`
estaban stubeadas (no-ops) por un refactor incompleto — ningun pago descontaba stock real.
Restaurado, con tests de regresion en `payment/tests.py`. Tambien corregido un bug de
`@transaction.atomic` que revertia silenciosamente el `Transaction.status = 'ERROR'` al detectar
stock insuficiente. Ver `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` y
`payment/.AGENT/docs/AUDITORIA_PAYMENT_WOMPI_2026-07-03.md` para el detalle completo (5 bugs
distintos encontrados y corregidos solo en esta app).

---

### technical_services — Servicios tecnicos

Archivo: `technical_services/api/views.py` (catalogo, todo `AllowAny` en lectura) +
`orders/api/service_orders.py` (**ciclo de vida de la solicitud/orden de servicio, no vive en
`technical_services`**).

| ViewSet | Endpoint | Permiso |
|---------|----------|---------|
| `TechnicalServiceViewSet` | `/api/v1/services/services/` (+ action `quotation/`) | AllowAny |
| `ServiceCategoryViewSet` | `/api/v1/services/categories/` | AllowAny |
| `ServiceLevelViewSet` | `/api/v1/services/levels/` | AllowAny |
| `ServiceVariantViewSet` | `/api/v1/services/variants/` (+ action `price_history/`) | AllowAny (list) / IsAdminUser (`price_history`) |
| `ServiceMaterialViewSet` | `/api/v1/services/materials/` | AllowAny |
| `ServiceConfigurationViewSet` | `/api/v1/services/configurations/` | AllowAny |
| `ServiceOrderViewSet` (vive en `orders`) | `/api/v1/orders/service-orders/` | ver seccion `orders` |

Services: `ServiceAssignmentCommands` (`assign_technician`, `auto_assign_technician`),
`TechnicianSelector.get_available_for_category()`, `ServiceCommands`
(`confirm_slot_on_payment`/`release_slot_on_failure`, enlazados al flujo de pago),
`ServicePricingCalculator.calculate_breakdown()`, `ServiceSelector.get_variant_quotation()`.

**Motor de Reglas de Costo Dinamicas:** `ServiceCostRule` (contextos `SETUP`/`OPERATIONAL`/`TAX`/
`DISCOUNT`, tipos `PERCENTAGE`/`FLAT`, global o por variante via `ServiceCostAssignment`). El
endpoint `GET /api/v1/services/services/<uuid>/quotation/?variant_uuid=&duration=&discount_pct=`
retorna un `breakdown` estructurado (base_amount, cost_rules, additions, discounts, IVA, total).

**N+1 corregido parcialmente 2026-07-03 (Fase 6, afecta `/api/v1/dashboard/services/` Y el
catalogo publico `/api/v1/services/services/`, mismo serializer):**
1. `TechnicalServiceSerializer.get_variants()` hacia `obj.variants.filter(is_deleted=False)` —
   un `.filter()` explicito en un manager **ignora cualquier `prefetch_related` declarado**
   (Django solo cachea `.all()`). Corregido filtrando en Python sobre `obj.variants.all()`.
2. Faltaba `variants__materials__product_variant__product` en el prefetch de
   `ServiceSelector.list_all_for_admin()`. Agregado.
3. `LaborCostCalculator.get_active_config()` consultaba `ServiceConfiguration` (un valor
   **global**, igual para toda la peticion) **una vez por cada variante serializada**. Agregado
   cache de 5 min, invalidado por signal `post_save`/`post_delete` en
   `technical_services/signals.py` (`ServiceConfiguration` tambien es editable desde Django
   Admin, no solo desde `ServiceConfigurationCommands` — la señal cubre ambos caminos).

Medido: **31 -> 23 queries** para listar 2 servicios con 1 variante + 1 material cada uno.
**Pendiente, no corregido (fuera del alcance aprobado):** `get_calculated_price()` y
`get_price_info()` en `ServiceVariantSerializer` llaman **cada uno por separado** a
`ServiceSelector.get_variant_quotation(obj)`, duplicando todo el calculo de precio por variante.
Arreglarlo de raiz requiere cambiar como el serializer invoca el calculo (computarlo una vez y
reusarlo en ambos campos), un cambio de diseño mas alla de agregar cache.

### Checkout en modal + Service Operations (2026-07-09, nuevo)

Dos evoluciones grandes sobre el flujo de solicitud de servicio, sin tocar el modulo `payment`:

1. **Checkout dentro de la SPA (nunca navega fuera):** `ServiceRequestWizard.vue` ahora abre
   `ServiceCheckoutModal.vue` (nuevo) en vez de una UI de pago inline — reusa `useWompiWidget.js`
   (compartido con Cart/Renting) que ya abria Wompi como iframe overlay. Nuevo
   `serviceCheckoutStore.js` (Pinia).
2. **`ServiceOperation`** — FSM post-pago separado de `OrderServiceDetail` (dominio comercial),
   11 estados (`READY_FOR_PLANNING` → ... → `CLOSED`, + `CANCELLED`), con conflicto real de
   agenda contra `accounts.ProfessionalAvailability` (nunca doble-reserva un tecnico). **Se crea
   ANTES del pago** (a diferencia de "Shop Operations"), al final de
   `ServiceCommands.request_service()` — decision explicita del usuario: todo servicio solicitado
   debe llegar de inmediato al panel de Operaciones, pagado o no (el board muestra un badge "Pago
   pendiente" y no permite depachar sin pago).
3. **Centralizacion:** asignacion de tecnicos y operacion de cada servicio se maneja 100% desde
   `/panel/servicios/operaciones` (`ServiceOperationBoard.vue`) — el board viejo de solo-asignacion
   (`TechnicianAssignmentBoard.vue`, ruta `/panel/servicios/asignacion-tecnicos`) sigue existiendo
   pero ya no esta en el menu del sidebar.
4. **Bug corregido (reporte real del usuario):** `auto-assign/` y el selector manual de tecnico
   usaban el mismo filtro estricto de categoria/especialidad — el admin no podia asignar
   manualmente a un tecnico fuera de esa coincidencia exacta aunque quisiera decidirlo el mismo.
   Se separo: `auto-assign` sigue con matching estricto, la asignacion manual ahora usa
   `TechnicianSelector.get_all_active_technicians()` (todos los tecnicos activos, sin filtro) —
   el administrador decide si esta calificado.

Endpoints nuevos: `/api/v1/service-operations/` (`ServiceOperationViewSet` — `plan/`,
`assign-technician/`, `unassign-technician/`, `notify-client/`, transiciones de estado,
`report-incident/`, `resolve-incident/`, `close/`, `dashboard/`, `available-technicians/`).

Ver `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` (§18 completo) para el
detalle.

---

### quotes — Cotizaciones (sistema CPQ, no un wizard simple)

> **[ACTUALIZADO 2026-07-03]** Este ya no es un flujo lineal GET/POST/PDF. Es un sistema de
> "Configure-Price-Quote" con plantillas por categoria/subcategoria y un **Constructor de
> Cuestionarios Tecnicos** — ver `project_quotes_questionnaire_engine` en memoria del proyecto.

Archivo: `quotes/api/views.py` — `QuotationViewSet` + ViewSets de plantillas.

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/quotes/quotations/` | GET, POST | IsAuthenticated (create: AllowAny para cotizacion de catalogo/custom) |
| `/api/v1/quotes/quotations/from-template/` | POST | IsAuthenticated — crea "Solicitud de Cotizacion" desde cuestionario, sin precios visibles al cliente |
| `/api/v1/quotes/quotations/<uuid>/send/` | POST | genera y envia PDF (Celery) |
| `/api/v1/quotes/quotations/<uuid>/add_attachment/` | POST | adjuntos |
| `/api/v1/quotes/quotations/<uuid>/download_pdf/` | GET | AllowAny |
| `/api/v1/quotes/quote-template-categories/` | GET | AllowAny |
| `/api/v1/quotes/quote-template-subcategories/` | GET | AllowAny (`?category=`) |
| `/api/v1/quotes/quote-templates/` | GET | AllowAny |

`Quotation.STATUS_CHOICES` tiene **10 estados**: `BORRADOR, RECIBIDA, EN_REVISION,
PENDIENTE_INFORMACION, COTIZADA, ENVIADA, ACEPTADA, RECHAZADA, VENCIDA, CANCELADA`, con
`QuotationTimeline` como historial append-only.

`QuoteTemplateModule` tiene tipos `EQUIPMENT`/`MATERIALS`/`LABOR`. `QuoteQuestion` +
`QuoteQuestionOption` son el motor del constructor de cuestionarios.

Admin: `GET /api/v1/dashboard/quotations/` — lista completa.
Services: `QuotationCommands`, `QuotationSelector`, `PdfService`

---

### marketing — Campanas y dashboards

| ViewSet | Endpoint | Permiso real |
|---------|----------|---------|
| `MarketingCampaignViewSet` | `/api/v1/marketing/campaigns/` | `IsAdminUser` (corregido 2026-07-03; ModelViewSet completo) |
| `FlashOfferViewSet` | `/api/v1/marketing/offers/` | `AllowAny` (corregido 2026-07-03; vitrina publica, selector ya filtraba `is_active=True`) |
| `AgentRunViewSet` | `/api/v1/marketing/agent-runs/` | `IsAdminUser` (corregido 2026-07-03) |
| `DashboardViewSet` | `/api/v1/marketing/dashboard/` | `IsAdminUser` (corregido 2026-07-03) |

Services: `MarketingSelector` (y comandos asociados). Existen ademas directorios `marketing/agent/`
y `marketing/channels/` con tareas Celery, sugiriendo un sistema de marketing asistido por IA
(`AgentRun`) mas alla de un CRUD de campanas — no se profundizo en esta pasada.

**Corregido 2026-07-03 (Fase 6, auditoria de BD):** `MarketingCampaign.__str__()` referenciaba un
campo `self.channel` inexistente (el real es `channels`, plural) -- `AttributeError` en cualquier
`str(campaign)`. `FlashOffer` gano un `CheckConstraint` "como maximo un target" (variant/
service_variant/equipment_variant) -- deliberadamente no "exactamente uno", porque una oferta sin
target (oferta general) es un caso valido ya presente en produccion. `db_index` agregado en
`is_active`/`start_time`/`end_time`. Ver `[[project_db_audit_duplicate_indexes]]`.

---

### renting — Equipos en alquiler

Archivo: `renting/api/views.py`

| ViewSet | Endpoint | Permiso real |
|---------|----------|-----------|
| `EquipmentViewSet` | `/api/v1/renting/equipment/` (+ `check-availability`) | AllowAny |
| `EquipmentVariantViewSet` | `/api/v1/renting/variants/` | AllowAny |
| `RentingCategoryViewSet` | `/api/v1/renting/categories/` | `AllowAny` (corregido 2026-07-03; ademas ahora excluye inactivos) |
| `RentingBrandViewSet` | `/api/v1/renting/brands/` | `AllowAny` (corregido 2026-07-03) |
| `RentalLaborViewSet` | `/api/v1/renting/labor/` | `AllowAny` (corregido 2026-07-03; ademas ahora excluye inactivos) |
| `RentalRequestViewSet` / `RentalRequestListCreateAPIView` | `/api/v1/renting/rental-requests/` | `IsBuyerOrAdmin` |
| `RentalOperationViewSet` | `/api/v1/renting/operations/` (**nuevo, 2026-07-07**) | admin — panel `/panel/ordenes/renting` |

`EquipmentVariant` confirma pricing dual: `rental_price_per_day` y/o `rental_price_per_hour`, al
menos uno obligatorio. `RentalRequest` confirma el wizard de 8 pasos (docstring literal en el
modelo) con `STATUS_CHOICES` de 8 estados (draft -> pending_validation -> pending_payment -> paid ->
confirmed -> in_operation -> finished / cancelled) y soporta pago `WOMPI`/`NEQUI`/`COD`.

Modelos adicionales no cubiertos por versiones previas de este doc: `RentalProjectAttachment`,
`RentalPeriod` (disponibilidad por solape de fechas, no descuento de stock), `EquipmentLogisticsConfig`,
`RentalCostRule`/`RentalCostAssignment`.

Services: `RentingCommands`, `EquipmentCommands`, `EquipmentVariantCommands`,
`RentingCategoryCommands`, `RentingBrandCommands`, `RentalLaborCommands`,
`RentingSelector`, `EquipmentVariantSelector`, `RentingSummaryProvider`

**Corregido 2026-07-03 (Fase 6, auditoria de BD) — bug de sobreventa real:**
`RentalRequestCommands.create_request()` verificaba disponibilidad (`RentingSelector.check_availability()`)
sin ningun bloqueo de fila; dos solicitudes concurrentes para el mismo `EquipmentVariant` y fechas
solapadas podian pasar ambas la validacion y sobrevender el mismo equipo fisico. Se agrego
`select_for_update()` sobre la variante al inicio de `create_request()`. Probado con un test de
concurrencia real (2 threads, `TransactionTestCase`). Tambien: N+1 en `RentalRequestViewSet.list()`
(`get_primary_image()` ignoraba el prefetch) y `db_index` faltante en `Equipment.is_active`/
`is_featured`. Ver `[[project_db_audit_duplicate_indexes]]`.

**Corregido 2026-07-29 — CRITICO, tumbaba TODO Django, no solo `renting`:**
`renting/services/presenters.py:14` importaba `from django.utils.text import truncate_words` —
funcion que no existe en Django 5 (eliminada del framework hace mas de una decada; nunca fue
valida en ninguna version reciente). Se usaba en 2 lugares del mismo archivo: `_present_reviews()`
(linea ~459, trunca el comentario de una reseña a 30 palabras) y `_present_seo()` (linea ~578,
trunca `meta_description` a 20 palabras si no hay una configurada manualmente). Como
`renting/services/__init__.py` importa `presenters` a nivel de modulo, y `marketing/services/
selectors.py` importa `RentingSummaryProvider` de `renting.services` para armar
`internal_ai_urls.py` (montado sin condicion en `ecommerce/urls.py`), el `ImportError` se
propagaba al cargar el URLconf raiz completo — Django no arrancaba en absoluto (`docker compose
up` lo mostraba como `ecommerce_sintel_django` en `unhealthy`/reinicio en loop, bloqueando por
`depends_on: condition: service_healthy` a `celery_worker`, `celery_beat` y `nginx`, que nunca
llegaban a iniciar). Root cause de codigo real (visto en logs): probablemente un import
"recordado" de una API de Django antigua/de otro framework, nunca ejecutado localmente sin Docker
antes de este incidente. Fix: reemplazado por la API real y vigente,
`Truncator(texto).words(n, truncate=' ...')` (`django.utils.text.Truncator`), en ambos usos.
Verificado reconstruyendo la imagen (`docker compose up -d --build django`) — contenedor paso a
`healthy` en ~20s y los 3 servicios dependientes arrancaron sin bloqueo.

### `RentalOperation` + `AvailabilityEngine` (2026-07-07, nuevo) — no capturado en v7

- **`RentalOperation`** — FSM post-pago separado de `RentalRequest` (10 estados,
  `READY_FOR_SCHEDULING` → ... → `COMPLETED`), con `assigned_dispatcher` (mismo
  `operations.DispatcherProfile` que usa "Shop Operations"), dashboard de KPIs server-side,
  incidencias, emails de ciclo de vida completos. Panel `/panel/ordenes/renting`
  (`RentalOperationBoard.vue`).
- **`AvailabilityEngine`, 2 fases:** Fase 1 — `pending_payment` ya no bloquea la agenda del
  equipo; el lock de disponibilidad se movio a `confirm_payment()`/`approve_manual_validation()`,
  con manejo explicito de `payment_conflict`/`refund_required` si dos solicitudes compiten. Fase
  2 — wizard de reserva con componentes nuevos (`AvailabilityPill`/`AvailabilityCard`/
  `RentalHourSelector`), panel `/panel/renta/solicitudes`.
- **Decision de UX ya tomada dos veces** (Renting y luego Technical Services): la "agenda"/
  calendario de operaciones se muestra como lista, no como grilla/Kanban real — no volver a
  proponer un calendario visual sin que el usuario lo pida explicitamente.

---

### organization — SSoT de datos institucionales — app nueva, no listada antes (2026-07-12)

Antes de esta app, la marca/contacto/redes sociales vivian repartidos entre modelos de `core`
(`SiteBrandConfig`, `CompanyContactInfo`, `FooterLink(category='social')`) y variables de entorno
sueltas en `settings/base.py`. `organization` los consolido en un unico dueno — **ninguna otra
app puede leer estos datos directamente**, todo pasa por `OrganizationSelector`/
`OrganizationCommands` (`core` los consume asi desde 2026-07-12, ver seccion `core` abajo).

Montada en `/api/v1/organization/` via `DefaultRouter`, 8 recursos (todos requieren
`IsAdminUser` para escritura; lectura publica solo donde `core` los reexpone via `site-config`/
`footer`):

| Recurso | Modelo | Notas |
|---|---|---|
| `company/` | `Company` | Singleton — nombre comercial, descripcion, ano de fundacion |
| `branding/` | `Branding` | Singleton — logo, favicon, tagline (separado de `Company` a proposito) |
| `contact/` | `ContactInfo` | Singleton — telefono, email, direccion, horario |
| `social-links/` | `SocialLink` | Lista — reemplaza `core.FooterLink(category='social')` |
| `email-settings/` | `EmailSettings` | Singleton — solo datos de negocio (`default_from_email`, `frontend_base_url`); el password SMTP sigue en `.env` a proposito |
| `domain-settings/` | `DomainSettings` | Singleton — dominio principal/panel/API |
| `seo-settings/` | `SeoSettings` | Singleton — meta title/description, imagen Open Graph |
| `legal-entity/` | `LegalEntityInfo` | Singleton — razon social, NIT, direccion fiscal, representante legal |

Todos los singletons siguen el mismo patron (`SingletonMixin.save()` desactiva cualquier otro
registro activo), sin signals de invalidacion de cache propia — `core` invalida
`SITE_CONFIG_CACHE_KEY`/`FOOTER_CACHE_KEY` explicitamente en `dashboard/api/views.py` justo
despues de cada `OrganizationCommands.upsert_*`.

Panel admin: `OrganizationView.vue` en `/panel/organizacion`, 8 tabs (uno por recurso de arriba).
Migro datos reales existentes via data migration (`core/migrations/0017_migrate_company_data_to_organization.py`)
antes de borrar los modelos viejos de `core` — sin perdida de datos en el traspaso.

**Nota (2026-07-20):** `organization/CLAUDE.md` todavia dice "Fase 3 de 9 completada", pero los 8
recursos de arriba estan todos operativos (verificado con los 8 endpoints reales y su consumo
activo desde `OrganizationView.vue` toda esta sesion) — esa nota de fase parece desactualizada,
no se corrigio en esta pasada (fuera del archivo pedido auditar).

---

### security — Auditoria de seguridad transversal — app nueva, no listada antes (~2026-07-09)

Dominio complementario (no reemplaza) a `users.UserAuditLog` (acciones administrativas) ni
`kyc.VerificationEvent` (timeline KYC) — enfocado en senales de seguridad: logins fallidos,
rate-limit alcanzado, archivos KYC rechazados, verificacion bloqueada/rechazada, y (2026-07-16)
`AI_ACTION_EXECUTED` para cada escritura que el AI Core ejecuta en nombre de un usuario real (ver
nota de AI Core mas abajo).

| Endpoint | Metodo | Permiso |
|---|---|---|
| `/api/v1/security/health/` | GET | `IsAdminUser` — snapshot de salud (`SecurityHealthView`) |
| `/api/v1/dashboard/security/*` | — | `AdminSecurityViewSet` (BFF admin, panel `/panel/seguridad`) |

Modelo: `SecurityEvent` (append-only, nunca se edita ni se borra, ni existe un endpoint de
escritura fuera del Command). Unico punto de escritura: `SecurityCommands.log_event(...)`, que
**nunca** propaga una excepcion al caller (solo deja constancia en el logger) — cualquier app
puede llamarlo con un import diferido (`from security.services.commands import SecurityCommands`
dentro del metodo, mismo patron que `notifications.dispatch_notification`) sin arriesgar romper
su propio flujo de negocio si el logging de seguridad fallara.

Services: `SecurityCommands.log_event()`, `SecuritySelector.list_events()`/`.get_health_snapshot()`.

---

### seo — Metaetiquetas del `<head>` — app nueva, no listada antes (2026-07-31)

Reemplaza el antipatron de hardcodear codigos de verificacion (Meta Business Suite, Google
Search Console...) directamente en `templates/spa_shell.html`. Modelo `SiteMetaTag`
(proveedor/tipo/meta_name/meta_content/html_snippet/prioridad/entorno/pagina destino) + audit log
append-only `SeoMetaTagAuditLog`. Renderizado 100% server-side: `templates/spa_shell.html` (unico
punto donde Django construye el `<head>` en produccion, ver `ecommerce/urls.py` +
`nginx-common.conf`) carga `{% render_meta_tags %}` (`seo/templatetags/seo_tags.py`), que lee un
cache de 300s poblado por `MetaTagSelector` — nunca hay insercion via JavaScript.

| Endpoint | Metodo | Permiso |
|---|---|---|
| `/api/v1/dashboard/seo/meta-tags/*` | GET/POST/PATCH/DELETE + `duplicate/`/`toggle/`/`reorder/`/`preview/`/`export/`/`import/`/`history/` | `ADMIN_PERMISSIONS` (`AdminSeoMetaTagViewSet`, BFF admin, panel `/panel/seo/meta-tags`) |

Sanitizacion sin dependencias nuevas: `seo/services/sanitizer.py::sanitize_meta_html()` (stdlib
`html.parser` + `format_html`), solo permite `<meta>` con atributos de una allowlist, rechaza
scripts/atributos `on*`/URIs `javascript:`. Seed inicial (verificacion de Meta Business Suite)
via data migration (`seo/migrations/0002_seed_meta_business_verification.py`), nunca hardcodeado.
Services: `MetaTagSelector`, `MetaTagCommands` — ver seccion completa en
`seo/.AGENT/docs/ARQUITECTURA_COMPLETA_SEO.md`.

---

### core — Contenido publico (landing, home feed) — app nueva, no listada antes

> **[MIGRADO 2026-07-12]** `core` ya NO es dueno de marca/contacto/redes sociales — se movieron a
> la nueva app `organization` (ver seccion dedicada arriba). `core` sigue exponiendo los mismos
> endpoints publicos (`site-config`/`footer`), pero ahora **consume** esos datos via
> `OrganizationSelector` en vez de poseerlos. `core` retiene solo contenido de la propia Home
> (banners, tarjetas, modulos, CTA, slider de marcas) y navegacion del sitio (`NavbarLink`,
> `FooterLink` categoria `nav`).

Mounted en `/api/v1/core/` via un unico `HomeFeedView(GenericViewSet)`, `permission_classes = []`
(publico, sin auth):

| Endpoint | Descripcion |
|---|---|
| `GET /api/v1/core/home-feed/` | Feed agregado de la landing (cache 5 min) — incluye `card_groups`/`footer_cta`, no solo `card_group_titles` (agregado 2026-06-30) |
| `GET /api/v1/core/footer/` | Configuracion de footer |
| `GET /api/v1/core/site-config/` | Branding/config global del sitio — hoy combina `organization.Company` + `organization.Branding` |
| `GET /api/v1/core/about-us/` | **Nuevo 2026-07-19** — filosofia institucional para la pagina publica `/nosotros` (historia/mision/vision/valores), `AboutUsConfig` (singleton) + `AboutUsValue` (lista). Admin: `/panel/nosotros`. Cache propia (`sintel_about_us_v1`), no viaja dentro de `home-feed` (es su propia pagina, no un bloque de la Home) |
| `GET /api/v1/core/enums/{name}/` | Catalogo contract-first de enums compartidos (badges/labels), consumido por `useEnums.ts` en TODO el panel admin, no solo landing |

**[CORREGIDO 2026-07-23]** 12 modelos, no 9 como decian versiones anteriores de este documento
(el conteo de "9" quedo congelado en la migracion `0014`, 2026-06-30, y nunca se actualizo tras
sumar `BrandSliderConfig`/`BrandSliderItem` -- migr. `0022` -- y `FooterGroup`/`FooterLink` --
migr. `0023`-`0025`; `AboutUsConfig`/`AboutUsValue` ya estaban referenciados aparte mas abajo en
este mismo documento pero no se habian sumado al conteo): `HomeBanner`, `HomeModuleConfig`,
`HomeCard`, `HomeCardGroup`, `FooterCTAConfig`, `FooterGroup`, `FooterLink`, `NavbarLink`,
`BrandSliderConfig`, `BrandSliderItem`, `AboutUsConfig`, `AboutUsValue`. `HomeModuleConfig`,
`HomeCard` y `HomeCardGroup` ganaron campos de un "Constructor Visual" (2026-06-30):
`display_type`/`layout_config` en `HomeModuleConfig` (18 layouts posibles),
`card_type`/`animation`/`is_featured`/`priority` en `HomeCard`,
`layout_type`/`padding`/`columns`/`bg_image` en `HomeCardGroup` — editado desde
`ModuleBuilderModal.vue` (nuevo, ~1500 lineas) en `/panel/home-config`. Cache invalidado via
signals (8 de 9 modelos del set original de contenido Home — `HomeCardGroup` es la unica
excepcion intencional, invalidacion manual en su ViewSet) + llamadas explicitas desde el panel
admin — no verificado en esta pasada (2026-07-23) si `BrandSliderConfig`/`BrandSliderItem`/
`FooterGroup`/`AboutUsConfig`/`AboutUsValue` (sumados despues del conteo original de 9) siguen
el mismo patron de invalidacion.

**N+1 corregido 2026-07-03 (Fase 6, tercera instancia del mismo patron):**
`get_thumbnail()` en `FeaturedProductCardSerializer`/`FeaturedEquipmentCardSerializer`/
`FeaturedServiceCardSerializer` (usados por `home-feed`) hacia
`obj.images.filter(is_primary=True).first()` + fallback `obj.images.first()` — un `.filter()`
explicito en el manager **ignora el prefetch_related('images')** ya declarado en cada
`list_featured()`. Corregido reutilizando `obj.images.all()` (cache de prefetch) + busqueda en
Python, igual patron que `get_min_price()` en el mismo archivo (que ya lo hacia bien). Severidad
menor que otros N+1 de esta sesion porque `home-feed` tiene cache de 5 min — el costo se paga una
vez por ventana de cache, no por visitante. `core` no tiene suite de tests (`core/tests.py` no
existe); se verifico manualmente contra datos reales (200 OK, thumbnails resuelven bien).

---

### notifications — Notificacion multicanal centralizada — app nueva, no listada antes

Todas las apps deben llamar `NotificationCommands.dispatch_notification()` en vez de enviar
notificaciones directamente (WebSocket, Email, WhatsApp via Meta Cloud API).

| Endpoint | Permiso |
|---|---|
| `GET /api/v1/notifications/logs/` | `IsAuthenticatedActiveUser` (solo lectura, propias) |
| `GET/POST /api/v1/notifications/preferences/` + `preferences/set/` | `IsAuthenticatedActiveUser` |

Modelos: `NotificationTemplate`, `NotificationLog`. 8 `NotificationTemplate` sembradas en BD (ver
memoria del proyecto).

**[AGREGADO 2026-08-17]** `notifications/tasks.py::process_whatsapp_inbound_task` es tambien el
canal WhatsApp del AI Core (Fase 7) — mensajes entrantes de WhatsApp (Meta Cloud API, webhook con
dedupe por `message_id`) resuelven el usuario por telefono y llaman al MISMO
`support.services.ai_bridge.ask_ai()` que usa el widget web, persistiendo ambos lados en la
`ChatRoom` real del usuario (visible en `/panel/soporte`, no un canal aislado). Desde 2026-08-17
respeta `is_ai_mode_active()`/`is_ai_rate_limited()` de la sala antes de auto-responder — ver
seccion `ai_engine` mas abajo.

---

### operations — Fulfillment operativo post-pago — app nueva, no listada antes

Orquesta tickets/asignaciones/tracking/documentos/reviews **sin poseer los datos comerciales de la
orden** (esos siguen en `orders`/`payment`).

| Endpoint | Permiso |
|---|---|
| `GET /api/v1/operations/my/` | `IsAuthenticatedActiveUser` — tickets propios del cliente |
| `/api/v1/operations/tasks/` | `IsOperationalUser`/`IsAdminUser` segun accion — personal operativo |
| `/api/v1/dashboard/operations/` | BFF admin separado |
| `ws/operations/<ticket_uuid>/` | WebSocket de tracking en vivo |

Modelos: `OperationTicket`, `OperationAssignment`, `TrackingEvent`, `DispatcherProfile`,
`OperationDocument`, `OperationReview`. `OperationCommands.ensure_tickets_for_order()` es llamado
desde `payment.shared.commands.confirm_order_payment()` y `CodCommands.confirm_order()`.

---

### support — Chat de soporte en tiempo real (WebSocket + 1 endpoint REST) — doc propio actualizado (ver AUDITORIA/15)

> **[CORREGIDO 2026-07-03, luego 2026-07-23]** El doc
> `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` describia una REST API completa
> (`ChatRoomViewSet`, `/api/v1/support/rooms/`) y un WebSocket por sala (`ws/support/<room_uuid>/`)
> que no existian en el codigo (corregido 2026-07-03: solo hay un WebSocket fijo, ver abajo). Esa
> correccion de 2026-07-03 quedo a su vez desactualizada: **desde entonces `support` SI gano una
> ruta REST real**, y las 2 afirmaciones "no existe `/api/v1/support/`" que este documento repetia
> (aqui y en la seccion "Rutas API raiz") eran incorrectas al momento de esta auditoria
> (2026-07-23) — confirmado leyendo `ecommerce/urls.py:68`.

**Lo que realmente existe hoy:**
1. Una unica ruta WebSocket fija `ws/support/chat/` -> `SupportChatConsumer`
   (`support/consumers.py`, registrado en `ecommerce/routing.py`). `connect()` distingue: admin
   (`is_staff and is_superuser`) se une al grupo global `support_admins`; cliente regular
   obtiene/crea su `ChatRoom` y se une a `chat_{user.uuid}`, recibiendo el historial de mensajes
   al conectar.
2. **[NUEVO, no capturado en ninguna version anterior]** `POST /api/v1/support/chats/<uuid>/rate/`
   (`support/api/views.py::RateConversationView`, `support/api/urls.py`, montado en
   `ecommerce/urls.py:68` sin prefijo adicional) — `IsAuthenticated`, calificacion CSAT (1-5 +
   comentario opcional) de una conversacion ya cerrada, via `ChatCommands.rate_conversation()`.
   El propio docstring del archivo lo llama explicitamente "primera REST API publica de
   `support`" — el resto de la interaccion sigue siendo 100% WebSocket, esto es un unico endpoint
   satelite, no un cambio de arquitectura.

Modelos: `ChatRoom` (`user`, `status` OPEN/CLOSED, `assigned_admin`, mas campos de CSAT:
`csat_rating`/`csat_comment`/`csat_rated_at`), `ChatMessage` (`room`, `sender`, `message`,
`is_read`), `ChatRoomContext` (no detallado en esta pasada).

UI: widget flotante para clientes (componente global, no una ruta) + consola admin
`SupportDashboardView.vue` en `/panel/soporte` (dos columnas: lista de salas + chat activo).

> **[RESUELTO 2026-07-31, AUDITORIA/15_AUDITORIA_SUPPORT_OMNICANAL.md]** El pendiente de abajo
> (actualizar el doc propio de `support` con el endpoint CSAT) ya se cerro, junto con 4
> desincronizaciones mas del mismo doc y 8 correcciones reales de codigo (bot IA mal atribuido en
> el historial REST, rate-limit de IA en el WS, visibilidad de caidas del AI Engine, validacion de
> estado en sala cerrada, duplicacion WS/REST de labels de contexto) — ver ese documento para el
> detalle completo.

**Pendiente (resuelto 2026-07-31):** actualizar `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` para incluir el
endpoint CSAT y el AI Core en modo "atencion IA" antes del Human Handoff — no se hizo en esta
pasada por estar fuera del archivo que se pidio auditar (ver "Tareas pendientes").

**[AGREGADO 2026-08-17, gap real de este documento — nunca se habia documentado aqui pese a
estar construido/probado desde 2026-07-16]** `SupportChatConsumer` no solo enruta
cliente<->admin: si la sala esta en modo IA (`is_ai_mode_active(room)` — ver seccion `ai_engine`
abajo), un mensaje de cliente dispara `_ai_reply()` (tarea async, no bloquea el socket), que
llama a `ai_bridge.ask_ai_async()`. La respuesta se persiste como `ChatMessage` del bot
(`AI_BOT_EMAIL`, `ai_metrics` JSON) y se difunde a AMBOS grupos (`chat_{user.uuid}` Y
`support_admins`) para que el panel admin vea la conversacion de la IA en vivo. Human Handoff:
si la IA ejecuta `abrir_ticket_soporte` con exito, `ChatRoom.ai_paused=True` y dejar de
responder en esa sala — la reactivacion real ocurre en una sala NUEVA (no existe un "unpause"
en la misma sala): `ChatCommands.get_or_create_room()` solo reusa salas `OPEN`, asi que tras
`close_room()` el siguiente mensaje crea una sala con `ai_paused=False` por default.

---

## Frontend SPA — Vue 3

> **[ACTUALIZADO 2026-07-03]** La estructura de directorios de alto nivel
> (`modules/`, `views/`, `store/`, `components/`) sigue siendo correcta, pero el router y las
> rutas cambiaron sustancialmente. Verificado leyendo `frontend/src/apps/admin/router.js`
> directamente (es el unico router real de toda la SPA, pese a estar en `apps/admin/`).

### Estructura real

```
frontend/src/
  apps/
    admin/       router.js (UNICO router — define TODAS las rutas: customer + /panel/*), App.vue,
                 main.js (UNICO entry point de Vite — ver nota abajo)
  main.js        # entrada raiz, trivial — la app real se monta desde apps/admin/
  modules/       # modulos ADMIN: shop/, inventory/, orders/, users/, services/, quotes/,
                 # renting/, marketing/, support/ (SupportDashboardView.vue)
  views/         # auth/, admin/, customer/{shop,renting,services,quotes,account,checkout}/
  store/         # Pinia: auth.js, cart.js
  components/    # layout/, ui/, customer/
  composables/   # useApi.js, useAuth.js, useToast.js, useOffcanvas.js
  data/, renderers/, services/, shared/
```

**No existe `frontend/src/router/`** como directorio separado — todo vive en
`apps/admin/router.js`.

**[CORREGIDO 2026-07-23]** `frontend/src/apps/customer/` **no existe** — versiones anteriores de
este documento decian que existia como "placeholder casi vacio". `frontend/vite.config.js`
(`rollupOptions.input`) define un unico entry point, `admin: resolve(__dirname,
'src/apps/admin/main.js')`, con un comentario explicito en el propio archivo ("admin: unico SPA
real"). La afirmacion de "Vite con multi-entry (admin + customer apps)" en la seccion
"Notas de infraestructura frontend" de abajo tambien queda corregida.

### Rutas reales (verificadas en `router.js`, no exhaustivas)

Publicas / portal comprador (bajo `/`): `inicio` (LandingView, **nueva, no listada antes**),
`tienda`, `tienda/producto/:uuid`, `alquiler` + subrutas, `servicios` + subrutas, `cotizar`,
`cotizar/catalogo`, `cotizar/personalizada`, `checkout`, `orden-confirmada`, `payment/result`
(retorno PSE), `checkout/nequi-espera`, `contratistas` + `:uuid` (**nuevo, marketplace de
contratistas**), `mis-tareas` (**nuevo, portal movil de personal operativo**).

`/mi-cuenta/*` (requiere auth): `perfil`, `pedidos`, `alquileres`, `wishlist` (**nuevo**),
`direcciones`, `tarjetas` (**nuevo**), `cotizaciones`, `perfil-profesional` (SSoT: wizard de
upgrade `ContractorOnboardingWizard.vue`, no un registro alterno), `verificacion` (**nuevo,
2026-07-06** — subir documentos KYC), `mi-agenda` (**nuevo**), `operaciones`, `operaciones/:uuid`.
`/registro-profesional` (top-level) es ahora solo un `redirect` a `/register` (2026-07-06) —
`RegisterContractorView.vue` se elimino, ya no existe un registro separado por tipo.

`/panel/*` (admin): agrega respecto a v7 `servicios/operaciones` (**nuevo, 2026-07-09** —
`ServiceOperationBoard.vue`, board centralizado de Operaciones de Servicios Tecnicos),
`servicios/asignacion-tecnicos` (board antiguo, ya no en el menu del sidebar pero la ruta sigue
viva), `ordenes/renting` (**nuevo, 2026-07-07** — `RentalOperationBoard.vue`), `renta/solicitudes`
(**nuevo, 2026-07-07**), `productos/operaciones` (**nuevo, 2026-07-09** — `ShopOperationBoard.vue`,
anidado en el grupo "Tienda" del sidebar), `validaciones` + `validaciones/:uuid` (**nuevo,
2026-07-06** — panel KYC), ademas de lo ya listado en v7: `home-config`, `soporte`, `operaciones`
+ `operaciones/:uuid`, `despachadores`, `dashboard`, `productos`, `categorias`, `marcas`,
`impuestos`, `ordenes`, `usuarios`, `servicios`, `s-categorias`, `s-niveles`, `profesionales`
(**nuevo, solo-lectura**), `cotizaciones` + `cotizaciones/plantillas/:uuid`, `renta` + subrutas,
`marketing`.

### Design System — `components/base/*` (2026-07-18/19, no releido a fondo esta pasada)

Biblioteca compartida cross-modulo, distinta de `components/customer/account/*` (Mi Cuenta,
2026-07-17) y de `components/shared/checkout/*` (Payment, `PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md`).
Nacio de fusionar duplicados casi-identicos entre Renting/Services/Shop/Operations/Support
(cards de catalogo, reseñas, FAQ, galerias, forms de Categoria/Marca, modales, badges de estado).
Componentes reales hoy: `BaseReviews`, `BaseAccordion`, `BaseGallery`, `BaseHorizontalCard`,
`BaseBrandForm`, `BaseCategoryForm`, `BaseModal` (dialogo centrado — deliberadamente NO fusionado
con `SintelOffcanvas`, que es panel lateral, patron distinto), `BaseContextCard`, `BaseStatusBadge`,
`BaseInput`/`BaseTextarea`/`BaseUpload` (primeros 3 del Grupo D de inputs, el resto -- `BaseSelect`,
`BaseAddress`, etc. -- no construidos todavia, solo se construyen contra un consumidor real). Ver
`ai_skills/frontend/components/cards.md` §2.1 para el catalogo completo con props, y
`frontend/.AGENT/doc/PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md` para la auditoria de
8 fases que lo origino. Migracion incremental por modulo, todavia en curso (Organization/Core/
Operations/Support ya migrados a esta fecha; Marketing/KYC/Notifications pendientes).

**Rutas nuevas no capturadas arriba:** `nosotros` (publica, `/nosotros`, AboutUsView.vue —
filosofia institucional, 2026-07-19) y su contraparte admin `nosotros` (`/panel/nosotros`,
AboutUsAdminView.vue, grupo "Sitio Web" del sidebar). El login/registro de cliente rediseñado
(2026-07-17) usa su propio `CustomerAuthLayout.vue` en vez de `CustomerLayout` para `/login` y
`/register` — ver nota en seccion `accounts` arriba.

**Corregidos 2026-07-29 — 2 bugs reales en las cards de catalogo, ambos afectando `/alquiler` y
propagados a Shop por componente compartido:**
1. **Mismatch de contrato con el backend (0 imagenes visibles).**
   `components/renting/EquipmentHorizontalCard.vue:3` leia `equipment.image || ''` y
   `components/customer/ui/ItemCard.vue:7-8` leia `item.image` — propiedad plana que
   `EquipmentSerializer`/`ProductSerializer` (backend) **nunca devuelven**; ambos siempre
   expusieron `images` (array de `EquipmentImageSerializer`/`ProductImageSerializer`, cada objeto
   con `image`/`is_primary`/`position`). Como ambos componentes se usan tambien para `type="rental"`
   y `type="product"` en Shop (`ItemCard.vue` es generico, no exclusivo de Renting), el bug era
   identico en las 2 vistas (grid y lista) de `/alquiler` y en la vista grid de Shop. Fix: computed
   `primaryImage`/`primaryImageUrl` en ambos componentes —
   `images.find(img => img.is_primary) || images[0]`. `RentalDetailView.vue:543` y
   `RentalBookingWizard.vue:561` ya leian `images` correctamente y no necesitaron cambio.
2. **Layout roto por imagenes en orientacion retrato.** `components/base/BaseHorizontalCard.vue`
   (ver "Design System" arriba — compartido Renting/Services/Shop) tenia `.bhc-img-wrap { height:
   100%; }` sin que ningun ancestro (`.row` -> `.col-auto`) declarara una altura explicita —
   el porcentaje se resolvia como `auto`, dejando que la altura intrinseca real de cada `<img>`
   (segun su aspect ratio) determinara la altura de toda la fila/card. Fix: altura fija
   (`140px` desktop, `120px` `@media (max-width: 575px)`) en vez de `100%` — con
   `object-fit: var(--bhc-image-fit)` la imagen ahora se adapta al box fijo, nunca al reves.
   `components/customer/ui/ItemCard.vue` (vista grid) ya usaba el truco de aspect-ratio fijo
   (`padding-top: 72%` + `img` en `position: absolute`) y no tenia este problema.

### Notas de infraestructura frontend

- **Vite** con un unico entry point (`admin`) — **[CORREGIDO 2026-07-23]** no es multi-entry,
  `frontend/src/apps/customer/` no existe (ver seccion "Estructura real" arriba)
- **HMR en Docker/WSL2:** `watch.usePolling: true, interval: 300` en `vite.config.js` — sin esto,
  los cambios Vue/JS nunca se reflejan en el navegador (inotify no funciona en WSL2)
- **Bootstrap 5.3.3 + Bootstrap Icons 1.11.3** via CDN en `index.html`
- **Inter font** (Google Fonts, pesos 300-800) via CDN

### Regla de endpoints frontend — CRITICA

```
LECTURA  (GET)                -> shop/ | renting/ | services/ | ...  (ReadOnly, sin auth)
ESCRITURA (POST/PATCH/DELETE) -> dashboard/products/ | dashboard/categories/ | ...  (JWT admin)
```

URL de escritura usa `item.id` (PK entero). FK en payloads usa `item.uuid` (SlugRelatedField).

**NUNCA llaman a `/api/v1/dashboard/`** desde el portal del comprador — ese prefijo es exclusivo
del panel admin.

---

### ai_engine — Motor de IA conversacional (Support Agent) — servicio Docker separado, seccion nueva 2026-08-17 (gap real: nunca tuvo su propia seccion pese a construirse desde 2026-07-16)

Directorio: `ecommerce_sintel/ai_engine/` — proceso FastAPI independiente (imagen Docker propia
`sintel_ai`, puerto 8100 interno, **NO** parte de `ecommerce/urls.py` ni del proceso
Django/Gunicorn). **Sin bind-mount de codigo** — un cambio ahi requiere
`docker compose build sintel_ai && docker compose up -d sintel_ai`; un `restart` simple no lo
recoge (confirmado empiricamente 2026-08-17).

**Responsabilidad unica: inteligencia conversacional del Customer via Support Chat.** `ai_editor`
(generacion/propuesta de codigo, ver v14-v16 arriba) es un modulo distinto y congelado — sin
conexion directa entre ambos (verificado por test AST). `ai_engine` tampoco importa
`project_knowledge_graph` (desacoplado FASE 0, 2026-08-10, ver
`ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md`).

**Flujo real**: `SupportChatWidget.vue` (o WhatsApp) → WebSocket `ws/support/chat/` / webhook
Meta → `support/services/ai_bridge.py` (identidad JWT real del usuario, nunca generica) →
`POST /chat` de `ai_engine` → `action_graph.py` (LangGraph): Intent → Agent Router (**9 Agent
Profiles** en `agents/profiles/*.yaml`: Support/Account/Admin/Marketing/Order/Payment/Rental/
Sales/Service, con escalamiento agente-a-agente hacia SupportAgent) → Customer Context
(`AiCustomerContextView`, cache Redis 5 min, solo 4 intents que lo necesitan) → RAG
(`retrieve_knowledge_for_chat`, filtra `visibility=="public"` — evita que el LLM fabrique
respuestas con documentacion tecnica interna, hallazgo real corregido 2026-08-08) → Tools
(**29 capabilities activas**, `capabilities/registry.py` + `tools/registry.py`; el LLM nunca ve
una Tool directa) → Policy Layer (deny/confirm/allow segun `ToolMetadata`, `interrupt()` real de
LangGraph para confirmacion humana, rate limit por-Tool en Redis) → respuesta — y vuelve por el
mismo camino.

**Puente con Django — `/api/v1/internal/ai/*`**: el include de `ecommerce/urls.py:70` expande a
**31 endpoints reales** (`ecommerce/internal_ai_urls.py`, uno por capacidad de negocio: ordenes,
alquileres, pagos, servicios, kyc, marketing, cotizaciones, core/CMS, etc.) — no "2 endpoints"
como decia una version anterior de la seccion "Rutas API raiz" arriba. `nginx` nunca expone
`sintel_ai` publicamente; `ai_engine` nunca toca el ORM directo, siempre pasa por estas vistas
(que a su vez usan Selectors/Commands ya existentes de la app dueña).

**Identidad y aislamiento**: `thread_id = f"{user_id}:{conversation_id}"` siempre deriva del JWT
resuelto server-side (nunca del mensaje del cliente) — un Customer no puede colisionar con la
conversacion de otro adivinando su `conversation_id`. `ChatRoom.ai_paused`/`assigned_admin`
(Django) gatea el Human Handoff via `is_ai_mode_active()`; el estado de turno (checkpoint Redis,
TTL 7 dias) lo posee `action_graph.py` — Django sigue siendo dueño de los datos de negocio.

**Canales**: Web (WebSocket) y WhatsApp (Meta Cloud API, `notifications/tasks.py`) llaman al
MISMO puente — motor channel-agnostic desde 2026-07-16. **[CERRADO 2026-08-17]** WhatsApp ahora
respeta `is_ai_mode_active()`/`is_ai_rate_limited()` de la sala antes de auto-responder — antes
un cliente cuyo chat web ya habia escalado a un humano seguia recibiendo respuestas automaticas
de la IA si escribia por WhatsApp.

**Concurrencia — [CERRADO 2026-08-17]**: el widget web ahora usa `ask_ai_async()`
(`httpx.AsyncClient`, espera nativa del event loop) en vez de `ask_ai()` sincrono envuelto en
`database_sync_to_async` — ya no ocupa el thread pool compartido de Django Channels durante la
llamada al AI Engine (hasta 300s). Esto cierra el item "B2" que la tabla de Tareas Pendientes de
este documento listaba como bloqueador antes de activar la IA ampliamente (ver abajo). WhatsApp
sigue usando `ask_ai()` sincrono sin cambios (contexto Celery, sin event loop que proteger).

**`AI_SUPPORT_CHAT_ENABLED`**: `True` en este entorno de desarrollo (confirmado en runtime,
2026-08-17, `ecommerce/settings/base.py`, default `False`). Produccion **no corre `sintel_ai` en
absoluto** — `docker-compose.prod.yml` excluye deliberadamente `sintel_ai`/`sintel_ollama`/
`sintel_chromadb` — el flag no aplica hoy contra produccion real.

Documentacion de detalle completo (no duplicada aqui): contrato tecnico —
[`SUPPORT_AGENT_SPEC.md`](../../ecommerce_sintel/ai_engine/.AGENT/SUPPORT_AGENT_SPEC.md);
checklist certificado con evidencia real, `APTA` —
[`SUPPORT_AI_CERTIFICATION.md`](../../ecommerce_sintel/ai_engine/.AGENT/SUPPORT_AI_CERTIFICATION.md);
23 capas E2E contra el stack vivo sin mocks —
[`CERTIFICACION_E2E_CHAT_IA_2026-08-13.md`](../../ecommerce_sintel/ai_engine/.AGENT/CERTIFICACION_E2E_CHAT_IA_2026-08-13.md).

---

### sms_bridge — Puente HTTP↔Modem GSM (HOST Windows) — modulo nuevo, detectado 2026-08-10

Archivo: `ecommerce_sintel/sms_bridge/bridge.py` — proceso Python que corre en el HOST Windows
**fuera de Docker**, no es una app Django ni un contenedor.

**Por que existe:** el contenedor Django (Linux, via Docker Desktop/WSL2) no puede abrir un puerto
COM de Windows directamente. El bridge actua como proxy HTTP entre el contenedor y el modem fisico.

**Modem:** SIM5360, SIM Movistar Colombia, puerto COM5, 115200 baudios.

**Protocolo AT:** modo texto (`AT+CMGF=1`), solicita reporte de entrega (`AT+CSMP=49,167,0,0`),
envio via `AT+CMGS`, termina con `Ctrl+Z`. Lock de threading: un solo SMS activo a la vez (el
modem AT no puede procesar comandos en paralelo).

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/status` | GET | Estado del modem: SIM (`AT+CPIN?`), senal (`AT+CSQ`), operador (`AT+COPS?`) |
| `/sms/send` | POST | Envia un SMS. Body: `{"to": "+57...", "message": "..."}` |

Auth: header `X-Bridge-Token` (debe coincidir con `SMS_BRIDGE_TOKEN` en `.env`). Si
`SMS_BRIDGE_TOKEN` no esta configurado, el bridge acepta peticiones sin autenticacion (log warning).

Variables de entorno:
```env
SMS_MODEM_PORT=COM5        # puerto serie del modem
SMS_MODEM_BAUD=115200
SMS_BRIDGE_HOST=0.0.0.0    # escuchar en todas las interfaces para host.docker.internal
SMS_BRIDGE_PORT=8765
SMS_BRIDGE_TOKEN=...       # debe coincidir con .env del backend
```

Cliente Django: `notifications/clients/sms.py`.
URL del backend: `SMS_BRIDGE_URL` en `ecommerce/settings/base.py`.
Iniciar: `python bridge.py` desde el host (requiere `pip install pyserial`).

---

### project_knowledge_graph — Site Knowledge Graph — modulo independiente (rediseno de 22 fases completo 2026-08-11)

Directorio: `ecommerce_sintel/project_knowledge_graph/` — analisis estructural del codigo del
proyecto (que existe, como esta relacionado, que se rompe si cambia, que tests correr, que
documentacion es relevante). Doc de arquitectura propio completo:
[`ARQUITECTURA_COMPLETA_GRAFO.md`](../../ecommerce_sintel/project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md)
(seccion 11 tiene el detalle fase por fase) y reporte de cierre ejecutivo:
[`SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md`](../../ecommerce_sintel/project_knowledge_graph/.AGENT/SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md)
— esta seccion es un resumen, esos dos documentos son la fuente de verdad detallada.

**Historia real (varias sesiones, no una sola pasada):**
1. **2026-08-08/09** — Extraccion fisica desde los archivos planos de `ai_engine/`
   (`project_map.py`, `knowledge_graph.py`, `dependency_graph.py`, `auditor.py`, familia
   "Graphify"). Los 9 archivos viejos se **borraron** de `ai_engine/`, no quedaron alias.
2. **2026-08-10, FASE 0** — Regla arquitectonica mas estricta adoptada: **"AI Engine no conoce
   ni importa `project_knowledge_graph`, y `project_knowledge_graph` no conoce ni depende de
   `ai_engine`."** `GraphImpactAnalysisTool` (la Tool de chat que exponia "que se rompe si cambio
   X" a un admin via conversacion) se **elimino por completo**, no se degrado, incluida su
   conexion como intent real del chat (`architecture_impact`). `main.py`/`planner.py`/`graph.py`/
   `incremental_updater.py` de `ai_engine` quedaron con stubs locales que ya no importan el
   grafo. Matriz exacta: `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md`.
3. **2026-08-10, FASES 1-2** — Nuevas entidades del grafo: `File`/`Symbol` (funcion/metodo Python
   con rango de lineas exacto) y `WebSocketRoute`/`EnvVar` ("Contract Graph" inicial).
4. **2026-08-10/11, FASES 3-21 — rediseno "Site Knowledge Graph -> Change Intelligence -> AI
   Editor Runtime" completo (22 fases totales, FASE 0-21).** Grafo estructural extendido a todo el
   dominio (frontend Vue/JS a nivel de simbolo, data flow de `Model.objects.verbo()` real,
   execution paths de signals/Celery tasks, test coverage, documentacion referenciada, infra
   Docker/nginx/env — FASES 3-9); capa de consulta para asistir cambios reales
   (`calculate_change_impact`/`resolve_change`/`build_graph_context_packet`/`graph_sdk` — FASES
   10-13); scaffold de un futuro AI Editor (`ecommerce_sintel/ai_editor/`, solo lectura, sin
   capacidad de modificar codigo — FASE 14, decision de seguridad deliberada); deteccion de
   cambios via git diff real, Change Validation Report, diseno documentado del Autonomous Change
   Loop (sin codigo, misma decision de seguridad que Fase 14), y auditoria de consultas — FASES
   15-18; consolidacion y limpieza documental — FASES 19-20; validacion global final (rebuild +
   suite completa, 0 regresiones) — FASE 21. Detalle fase por fase, cada uno con bugs reales
   encontrados y corregidos verificados contra el repo real (no fixtures): ver
   `ARQUITECTURA_COMPLETA_GRAFO.md` seccion 11.

**Decision arquitectonica (estado real a 2026-08-12, v16 -- actualizado desde el "SCAFFOLD, no
funcional" de v14/2026-08-11, ver seccion "Ultima revision" arriba para el detalle completo):**
```
ai_engine          -> chatbot de soporte puro (WebSocket, RAG, Action Graph) -- NO conoce el grafo
project_knowledge_graph -> Site Knowledge Graph (conocimiento estructural verificable del sitio),
                     COMPLETO: grafo + capa de consulta + SDK + deteccion de cambios + validacion
ai_editor/          -> AI Editor Runtime + AI Change Proposal Engine, FUNCIONAL de punta a punta
                     (plan de 60 fases completo al 2026-08-12): LLM -> PatchProposal estructurada
                     -> 10 capas de validacion real -> sandbox -> revision humana -> promote/
                     rollback contra el repo real, confirmado funcionando (FASE 54-55). El unico
                     limite que sigue siendo deliberado (no pendiente): ni `generation/` ni
                     `agent/` pueden LLEGAR a escribir sobre el workspace real por si solos --
                     promover exige siempre `decision`/`confirm` explicitos de un humano
                     (`generation.promotion.review_and_promote()`), nunca automatico.
```

**Estructura real (fisica y de contenido, verificada 2026-08-11, no aspiracional):**
```
project_knowledge_graph/
  __init__.py, config.py
  scanner/          # python_scanner.py, django_scanner.py, frontend_scanner.py, project_scanner.py
  project_map/      # builder.py, loader.py, query.py
  knowledge_graph/  # builder.py, loader.py, query.py (18 funciones), relations.py,
                     #   enrichers/ (documentation.py, docker.py, nginx.py, agents.py)
  dependency_graph/ # builder.py, loader.py, blast_radius.py, impact.py, query.py
  incremental/      # diff.py (deteccion de apps Y de simbolos individuales via git diff), hashing.py, updater.py
  audit/            # auditor.py (pipeline explicito), validator.py (6 chequeos),
                     #   change_validation.py (Change Validation Report), query_log.py (auditoria de consultas),
                     #   visualizer.py
  snapshots/        # manager.py (historial ligero de cada corrida, NO copia del grafo completo)
  graph_sdk/        # fachada estable de 13 operaciones, instrumentada con logging de auditoria
  cli/              # main.py -- `python -m project_knowledge_graph.cli <audit|impact|resolve-change|...>` (19 subcomandos)
  data/             # PROJECT_MAP.json, KNOWLEDGE_GRAPH.json, DEPENDENCY_GRAPH.json, QUERY_AUDIT_LOG.jsonl (untracked, no gitignored)
  tests/            # 120 tests, unit + integracion contra el repo real (no mockeado)

ecommerce_sintel/ai_editor/  # (paquete SEPARADO, no dentro de project_knowledge_graph) -- 12
  #                            submodulos, TODOS con logica real (ver "Ultima revision" v16 arriba)
  graph_client/     # wrapper de solo lectura sobre graph_sdk -- la UNICA frontera hacia el grafo
  llm/              # cliente LLM independiente (ollama/openai/anthropic), propio de ai_editor
  intent/, resolver/, planner/  # ChangeIntent -> ChangeContext -> ChangePlan, contra el grafo real
  repository/, patch/, validation/  # sandbox aislado, Patch Engine, validacion de sintaxis
  approval/, audit/  # Human Approval Gate, Change Audit (log append-only sanitizado)
  generation/       # 24 submodulos, FASE 24-50/56-59 -- AI Change Proposal Engine (LLM ->
                     #   PatchProposal estructurada -> validacion -> sandbox -> promote/rollback)
  agent/            # FASE 51-53 -- run_autonomous_change_loop(), orquesta todo lo anterior en
                     #   una sola llamada, sin poder LLEGAR a promover (garantizado por test AST)
```

**Escala real (ultima corrida real, verificada en FASE 21, 2026-08-11):** 9575 nodos / 20335
aristas — 21 apps Django, 150 endpoints, 1161 archivos, 6396 Symbol (857 marcados `is_test`), 432
Serializer, 168 ViewSet, 167 Model, 19 Task, 68 EnvVar, 4 WebSocketRoute, 8 Port, 6 NginxRoute, 29
Tool, 9 Agent. **120/120 tests pasan.**

**Limitaciones reales conocidas, documentadas y sin resolver a proposito** (lista completa en
`SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md` seccion 4):
1. `ai_engine/memory_builder.py`/`ai_manifest.py`/`specialized_retrieval.py` leen
   `ai_engine/PROJECT_MAP.json` directo de disco (no importan este modulo) — desde FASE 0 nada
   dentro de `ai_engine` regenera ya ese archivo, queda como foto estatica. Decision de
   arquitectura pendiente (`AI_ENGINE_KG_DECOUPLING_FASE0.md` seccion 3).
2. El REBUILD del grafo sigue siendo completo aunque la DETECCION de cambios ya es symbol-level
   (Fase 15) — convertir el builder en incremental real es un cambio de arquitectura mayor.
3. 8 endpoints reales sin arista `SERIALIZES` (gap de cobertura del enricher, no de esta fase).

---

## Infraestructura Docker (verificado 2026-07-03 via `docker ps`)

| Servicio | Imagen | Puerto externo | Healthcheck |
|----------|--------|----------------|-------------|
| `ecommerce_sintel_django` | `ecommerce_sintel:runtime` (Daphne ASGI) | 8000 | `GET /api/v1/health/` — ahora real: db+redis (503 si fallan) |
| `ecommerce_sintel_celery_worker` | `ecommerce_sintel:runtime` | - | `celery -A ecommerce inspect ping` |
| `ecommerce_sintel_celery_beat` | `ecommerce_sintel:runtime` | - | **`grep -a -l celery /proc/[0-9]*/cmdline`** (AUDITORIA/31 — antes sin healthcheck) |
| `ecommerce_sintel_db` | postgres:16-alpine | 5432 | nativo postgres |
| `ecommerce_sintel_redis` | redis:7.2-alpine | 6380 (mapeado, interno 6379) | nativo redis |
| `ecommerce_sintel_nginx` | nginx:1.26-alpine | 80 | - |
| `ecommerce_sintel_frontend` | node:24-bookworm-slim | 5173 | - |
| `ecommerce_sintel_ai` | `ecommerce_sintel_ai:latest` (FastAPI, AI Engine) | 8100 | — solo en dev, no en `docker-compose.prod.yml` |
| `ecommerce_sintel_ollama` | ollama/ollama:latest | 11434 | - |
| `ecommerce_sintel_chromadb` | chromadb/chroma:0.5.23 | 8200 | - |

**Componente fuera de Docker — `sms_bridge`** (`ecommerce_sintel/sms_bridge/bridge.py`): proceso
Python corriendo en el HOST Windows, no en ningun contenedor. Abre el puerto COM5 (modem GSM
SIM5360, SIM Movistar Colombia) y expone una API HTTP minima en `0.0.0.0:8765` que el contenedor
Django puede alcanzar via `host.docker.internal:8765`. Autenticacion: header `X-Bridge-Token`
(debe coincidir con `SMS_BRIDGE_TOKEN` en `.env`). Endpoints: `GET /status` (estado del modem) y
`POST /sms/send` (`{"to": "+57...", "message": "..."}` — serializa el acceso AT con un lock, un
solo SMS activo a la vez). Iniciar con `python bridge.py` desde el host; requiere `pyserial`.
Cliente en Django: `notifications/clients/sms.py`. URL: `SMS_BRIDGE_URL` en
`ecommerce/settings/base.py`.

**Atencion:** esta maquina aloja tambien contenedores `crm_sintel-*` (proyecto distinto) que
compiten por los puertos 80/5432. Verificar con `docker ps` antes de operar (exec/restart/stop).

Healthcheck publico: `GET /api/v1/health/` -> `{"status": "ok", "db": true, "redis": true, "celery": true}`
(503 si db o redis no estan disponibles desde Django — **CORREGIDO 2026-08-03**, AUDITORIA/29 P1).

Archivos media: servidos en dev via `static(MEDIA_URL, document_root=MEDIA_ROOT)` en `urls.py`.
`MEDIA_ROOT = BASE_DIR / 'media'`, `MEDIA_URL = '/media/'`

**Para correr tests del backend:** no hay Django instalado en ningun `.venv` local — usar
`docker exec ecommerce_sintel_django python manage.py test <app>` contra el stack ya levantado.

---

## Configuracion `.env` — Variables requeridas (corregido 2026-07-03, luego 2026-07-23)

| Variable | Uso |
|----------|-----|
| `WOMPI_PUBLIC_KEY` | Clave publica Wompi (checkout URL) |
| `WOMPI_PRIVATE_KEY` | Clave privada Wompi |
| `WOMPI_INTEGRITY_SECRET` | Firma SHA256 del checkout — **antes decia `WOMPI_INTEGRITY_KEY`, nombre real corregido** |
| `WOMPI_EVENTS_SECRET` | Verificacion de firma del webhook — **antes decia `WOMPI_EVENTS_KEY`, nombre real corregido** |
| `WOMPI_ENVIRONMENT` | `test` \| `prod` |
| ~~`WOMPI_WIDGET_URL`~~ | **[CORREGIDO 2026-07-23] NO es una variable de `.env`** — esta hardcodeada en `ecommerce/settings/base.py:373` (`'https://checkout.wompi.co/widget.js'`), no leida via `config(...)`. Eliminada de esta tabla |
| `NEQUI_CLIENT_ID` / `NEQUI_CLIENT_SECRET` / `NEQUI_API_KEY` / `NEQUI_ENVIRONMENT` | Integracion Nequi Push |
| `SECRET_KEY` | Clave secreta Django — **[CORREGIDO 2026-07-23]** antes decia `DJANGO_SECRET_KEY`, nombre real es `SECRET_KEY` (`config('SECRET_KEY')` en `settings/base.py:11`) |
| `JWT_SECRET_KEY` | **[AGREGADO 2026-07-23]** signing key de SimpleJWT (`SIGNING_KEY` en `settings/base.py:241`) — variable obligatoria, no estaba en ninguna version anterior de esta tabla |
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_PORT` | Conexion PostgreSQL — **[CORREGIDO 2026-07-23]** `DATABASE_URL` eliminada de esta tabla: no se usa en ningun lugar del codigo (grep completo sin resultados), la conexion real solo lee estas 5 variables sueltas (sqlite si `DB_HOST` no esta seteado, en dev local sin Docker) |
| `CORS_ALLOWED_ORIGINS` | Origenes permitidos CORS |
| `REDIS_URL` | Conexion Redis (broker Celery + channels) |

---

## API Docs

| URL | Descripcion |
|-----|-------------|
| `/api/docs/` | Swagger UI (drf-spectacular) |
| `/api/schema/` | OpenAPI 3 schema JSON |
| `/admin/` | Django Admin |

---

## Reglas criticas del proyecto

1. **No emojis en archivos .py** — causa `SyntaxError` -> 500 Internal Server Error.
2. **No cambiar `DJANGO_SETTINGS_MODULE`** sin instruccion explicita.
3. **Importar `IsAdminUser` desde `users.api.permissions`**, no desde `rest_framework.permissions`.
4. **Soft-delete siempre completo:** `is_active=False` + `is_deleted=True` (cuando el modelo tenga
   ambos campos).
5. **Selectores admin filtran `is_deleted=False`** — nunca `Model.objects.all()` en admin.
6. **Precios con `Decimal`**, nunca `float` (`min_value=Decimal('0.01')`).
7. **Toda logica de negocio en Commands/Selectors** — los ViewSets son orquestadores.
8. **Notificaciones siempre via `NotificationCommands.dispatch_notification()`** dentro de
   `transaction.on_commit(...)` — no `ws_notify` directo (app `notifications`, centralizada
   desde 2026-06).
9. **Compilar antes de hacer commit:** `python -m py_compile archivo.py`.
10. **Uploads de imagen (Category.image, Brand.logo):** usar `FormData` en el frontend — los
    ViewSets tienen `MultiPartParser, FormParser, JSONParser`.
11. **`WOMPI_EVENTS_SECRET` debe estar en `.env` en produccion** — sin ella el webhook no verifica
    firmas (nombre real, no `WOMPI_EVENTS_KEY`).
12. **La app de pagos se llama `payment`, nunca `wompi`** — verificar siempre contra
    `payment/apps.py` y `ecommerce/urls.py` antes de asumir nombres de ruta.
13. **SKU de `ProductVariant` es siempre auto-generado** (`_generate_variant_sku()`) — nunca
    aceptar SKU manual del usuario en serializers de creacion/edicion de variante.
14. **Antes de restaurar codigo desde un archivo `.bak`**, verificar que realmente representa el
    comportamiento correcto (no asumir que "mas viejo" = "correcto") — confirmar contra los
    comandos/consumidores reales del campo o funcion en cuestion.
15. **Un comentario `# ALGO_REMOVED: ... -> usar X o signal`** no es evidencia de que `X` o el
    signal existan — verificar antes de construir sobre esa base.
16. **Nunca nombrar una `@action` de DRF `dispatch`** — sobreescribe silenciosamente
    `View.dispatch()` y rompe TODAS las requests del ViewSet (solo un test HTTP real lo detecta,
    no un test de "comando" aislado). Descubierto 2026-07-08 en `technical_services`.
17. **Nunca `getattr(user, 'profile'/'technician_profile'/'dispatcher_profile', None)` directo**
    en codigo nuevo — usar `accounts.services.ProfileResolver` (`get_profile`/
    `get_technician_profile`/`get_dispatcher_profile`/`resolve*`). Ver seccion RBAC.
18. **`UserProfile.user_type` solo cambia en un lugar:** `kyc.services.commands.KycCommands._apply_requested_user_type()`,
    al aprobar un upgrade. Ningun modulo de negocio (Renting, Technical Services, Shop, Orders,
    Operations, Payment, Dashboard) debe escribirlo directamente, ni siquiera para un admin.

---

## Correcciones y mejoras aplicadas (2026-07-03 — auditoria completa payment/orders/cart/shop/dashboard/technical_services)

| App | Cambio | Severidad |
|---|---|---|
| `payment/shared/commands.py`, `payment/online/services/commands.py` | Restaurada deduccion real de inventario y validacion de stock (estaban stubeadas) | CRITICO |
| `payment/online/services/commands.py` | Corregido bug de `@transaction.atomic` que revertia `Transaction.status='ERROR'` silenciosamente | CRITICO |
| `payment/online/api/views.py`, `payment/nequi/api/views.py`, `orders/api/service_orders.py` | Corregidas 3 instancias de `order.status != 'pending'` (legacy) -> `Order.STATUS_PENDING_PAYMENT` | CRITICO (bloqueaba checkout completo) |
| `orders/services/commands.py` | Restaurada llamada a `CodCommands.confirm_order()` en `create_from_cart()` (checkout COD no confirmaba nunca) | CRITICO |
| `payment/cod/services/commands.py` | `CodCommands.confirm_order()` ahora transiciona `order.status = STATUS_PAID` | FUNCIONALIDAD |
| `cart/services/commands.py` | Restaurada validacion real de stock en `_check_availability()` y `checkout_cart()` | ALTO |
| `shop/services/summary.py` | Restaurado calculo real de estadisticas de inventario (devolvia ceros hardcodeados) | MEDIO |
| `orders/tests.py`, `cart/tests.py`, `dashboard/tests.py`, `technical_services/tests.py` | Corregidos imports/mocks rotos que causaban `NameError`/`AttributeError` antes de ejecutar los tests | ALTO (tests no detectaban regresiones) |
| `dashboard/tests.py` | Eliminada `DashboardInventoryAPITestCase` (probaba rutas `/api/v1/dashboard/inventory/` ya migradas a `/api/v1/inventory/`) | LIMPIEZA |
| Todo el proyecto | Eliminados los 8 archivos `.bak` restantes del patron `INVENTORY_REMOVED` | LIMPIEZA |
| `shop/management/commands/seed_product_sale_flow.py` | Restaurados imports + corregido `variant.fixed_price` -> `variant.price` (campo inexistente en `ProductVariant`) | BAJO (script de dev) |

Ver `payment/.AGENT/docs/AUDITORIA_PAYMENT_WOMPI_2026-07-03.md` para el informe completo con
matrices de riesgo, dependencias y estrategia de rollback.

---

## Correcciones y mejoras aplicadas (2026-06-20 — segunda ronda)

| Archivo | Cambio |
|---------|--------|
| `renting/api/views.py` | `from users.api.permissions import IsAdminUser` — reemplaza `permissions.IsAdminUser()` en `EquipmentViewSet`, `EquipmentVariantViewSet`, `RentingCategoryViewSet`, `RentingBrandViewSet`, `RentalLaborViewSet` |
| `shop/api/views.py` | Nueva action `GET /shop/products/<uuid>/reviews/` (AllowAny) — retorna resenas paginadas con `is_verified_purchase` |
| `shop/api/views.py` | Import `ProductReview` añadido |
| `CategoryForm.vue` | Upload de imagen con preview, FormData cuando hay archivo |
| `BrandForm.vue` | Upload de logo con preview, FormData cuando hay archivo |
| `ProductForm.vue` | Campos `short_description` y `video_url` en tab General |
| `ProductForm.vue` | Campos logistica (`weight`, `length`, `width`, `height`) en nueva variante y edicion inline |
| `ProductDetailView.vue` | Fix: `GET shop/products/${uuid}/` en vez de list query incorrecta |
| `ProductDetailView.vue` | Display de `short_description` como subtitulo del producto |
| `ProductDetailView.vue` | Embed de video YouTube/Vimeo (iframe) o fallback link |
| `ProductDetailView.vue` | Display de logistica de la variante seleccionada (peso, dimensiones) |
| `ProductDetailView.vue` | Seccion de resenas: lista con badge `Compra verificada` (`is_verified_purchase`) y formulario para autenticados |
| `.env` | `WOMPI_EVENTS_KEY` verificado — valor test presente, webhook signature activa |

> Nota 2026-07-03: la variable real se llama `WOMPI_EVENTS_SECRET`, no `WOMPI_EVENTS_KEY` — ver
> seccion de configuracion `.env` arriba.

---

## Correcciones y mejoras aplicadas (2026-06-20)

| Archivo | Cambio | Severidad |
|---------|--------|-----------|
| `orders/api/views.py` | `get_object_or_404` movido al bloque de imports (estaba al final del archivo) | CRITICO |
| `orders/api/views.py` | `permission_classes = [permissions.IsAuthenticated]` declarado explicitamente en `ShippingAddressViewSet` y `OrderViewSet` | ADVERTENCIA |
| `wompi/api/views.py` | Funcion `_verify_wompi_event_signature()` implementada — verifica SHA256 usando `WOMPI_EVENTS_KEY` | CRITICO (seguridad) |
| `wompi/api/views.py` | Webhook retorna 401 si la firma es invalida | CRITICO (seguridad) |
| `shop/api/serializers.py` | Cascada de campos nuevos: `Category.image`, `Brand.logo`, `Product.short_description/video_url`, `ProductVariant.weight/length/width/height`, `ProductReview.is_verified_purchase` | FUNCIONALIDAD |
| `shop/services/commands.py` | `CategoryCommands`, `BrandCommands`, `ProductCommands`, `ProductVariantCommands` actualizados con nuevos campos | FUNCIONALIDAD |
| `shop/services/selectors.py` | `CategorySelector.LIST_FIELDS` incluye `image`; `BrandSelector` incluye `logo` en `.only()` | FUNCIONALIDAD |
| `shop/api/views.py` | `search_fields` incluye `short_description`; `parser_classes` para Category/Brand | FUNCIONALIDAD |
| `dashboard/api/views.py` | `AdminCategoryViewSet` y `AdminBrandViewSet` con `parser_classes`; `create_brand` pasa `ser.validated_data` completo | FUNCIONALIDAD |
| `dashboard/services/admin_orchestrators.py` | `ShopAdminOrchestrator.create_brand(data)` delega `**data` a `BrandCommands` | FUNCIONALIDAD |
| Migracion `shop/0004` | Aplicada correctamente — 12 cambios de campo en 5 modelos | FUNCIONALIDAD |

> Nota 2026-07-03: las referencias a `wompi/api/views.py` en esta tabla historica corresponden al
> archivo que hoy es `payment/online/api/views.py` — la app nunca se llamo `wompi` en el codigo,
> pero el nombre de archivo real cambio desde entonces. Ver seccion `payment` arriba.

---

## Cambios recientes (2026-06-19)

| Estado | Cambio |
|--------|--------|
| Hecho | Implementar Wompi: firma de integridad SHA256 en `initialize_transaction()` |
| Hecho | Implementar Wompi: endpoint `transaction-status/` para post-pago |
| Hecho | Reescribir `OrderConfirmedView.vue` con 3 estados (APPROVED/PENDING/DECLINED) |
| Hecho | `goToWompi()` siempre llama `initialize` fresco (no reutiliza checkout URL) |
| Hecho | Redirect URL siempre incluye `?tx=<uuid>` sin restriccion HTTPS |
| Hecho | Fase 7: TechnicianProfile, ServiceAssignmentCommands, auto-asignacion jerarquica |
| Hecho | ServicePriceHistory — auditoria de cambios de precio con modal timeline en Vue |
| Hecho | Suite de pruebas 32/32 pasadas |

---

## Tareas pendientes (actualizado 2026-08-10)

| Prioridad | Tarea |
|-----------|-------|
| Media | Propagar los 3 incidentes del 2026-07-29 a los docs de Nivel 2: `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` y `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` (seccion "Cambios Recientes" propias, per protocolo de sincronizacion) — pendiente desde v11 |
| Media | Auditar si existe el patron `.image`/`item.image` (propiedad plana inexistente) en consumidores de `images[]` de `technical_services` y `quotes` — solo se verificaron Renting/Shop en v11 |
| Media | `organization/CLAUDE.md` dice "Fase 3 de 9" pero los 8 recursos estan operativos — corregir esa nota |
| Media | Documentar en `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` el Design System `components/base/*` al mismo nivel de detalle que `ai_skills/frontend/components/cards.md` |
| Media | Crear doc de arquitectura para `sms_bridge` (detectado 2026-08-10, sin doc propio) — variables de entorno, protocolo AT, casos de fallo, integracion con `notifications` |
| Media | Decidir como resolver la staleness de `ai_engine/PROJECT_MAP.json` (leido por `memory_builder.py`/`ai_manifest.py`/`specialized_retrieval.py`, ya no regenerado por nadie desde la FASE 0 de desacoplamiento de `project_knowledge_graph`, 2026-08-10) — ver `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md` seccion 3 para las 3 opciones evaluadas |
| Media | Rotar credenciales expuestas en `notas.txt` (P1-03 de AUDITORIA/33) y verificar historial Git/backups donde pudo haber circulado el archivo |
| Media | Replica de backups a destino fuera del host de produccion (P2-01 de AUDITORIA/33 — backups hoy en `C:\Users\Administrator\sintel_backups`, mismo host que los datos) |
| Baja | Confirmar si `core.CACHE`/signals cubren `BrandSliderConfig`/`BrandSliderItem`/`FooterGroup`/`AboutUsConfig`/`AboutUsValue` (5 modelos sumados despues del conteo original de "9") |
| Baja | Rate limiting en login (brute force) — verificar si el rediseno de Auth 2026-07-17 ya lo cubre |
| Baja | Implementar rol/perfil VENDOR completo (hoy reservado, sin flujo end-to-end) |
| Baja | Agregar test parametrizado que confirme `IsAdminUser` en ViewSets de `dashboard` |
| ~~Pendiente — requiere alcance mayor~~ **RESUELTO 2026-08-17** | ~~B2 de Fase 4: `ask_ai()` bloquea el thread pool compartido de `sync_to_async`~~ — nueva `ask_ai_async()` (`httpx.AsyncClient`) en `SupportChatConsumer`, ya no ocupa el pool compartido. Ver seccion `ai_engine` arriba y `ai_engine/.AGENT/SUPPORT_AI_CERTIFICATION.md` |
| Pendiente — requiere alcance mayor | Paginacion de historial de sala de soporte (A4 de Fase 4) — feature nueva backend+frontend |
| Pendiente — requiere alcance mayor | Historial de cambios (`changed_by`) para `EmailSettings`/`ContactInfo` en `organization` (Fase 10) — requiere modelo de auditoria nuevo |
| Descartado (2026-07-09) | Sistema de eventos de dominio, wizard de upgrade independiente por tipo, reorganizacion de dashboard de usuarios por tipo, libreria de 8 componentes Vue de identidad — sin consumidor concreto, ver `accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md` |

### Completadas (2026-08-17 — Auditoria E2E de cierre del AI Engine / Support Agent)

**Gap real de este documento, cerrado hoy**: el thread completo de trabajo del AI Engine como
Support Agent (separacion Support/Engineering, RAG governance, cost control, 9 Agent Profiles,
certificacion E2E contra el stack vivo, auditoria white-label) se ejecuto en varias sesiones
entre 2026-08-08 y 2026-08-14 sin que `IMPLEMENTATION_SUMMARY.md` lo reflejara — este documento
solo trackeaba el thread paralelo de `ai_editor`/`project_knowledge_graph` (v13-v16 arriba). Se
agrego la seccion `### ai_engine` (ver "Apps y estado de implementacion") validada contra el
codigo real, y se cerraron los gaps puntuales que las certificaciones previas (2026-08-08,
2026-08-13) habian dejado abiertos:

- WhatsApp ahora respeta `ai_paused`/`is_ai_mode_active` de la sala antes de auto-responder
  (`notifications/tasks.py`) — antes seguia respondiendo aunque el chat web ya hubiera escalado
  a un humano.
- `ask_ai_async()` (`httpx.AsyncClient`) reemplaza el uso de `ask_ai()` envuelto en
  `database_sync_to_async` dentro de `SupportChatConsumer` — cierra el B2 de la tabla de Tareas
  Pendientes (ver arriba), verificado con test real: 12 turnos de IA de 0.5s concurrentes
  terminan en ~0.5s, no ~6s.
- Rate limit por-Tool migrado de memoria del proceso a Redis (`action_graph.py`), mismo patron
  que `cost_control.py` — preciso aunque `sintel_ai` corra en mas de una replica.
- Nuevos tests de regresion: entrega real a `support_admins` con una sesion admin simultanea
  (brecha abierta desde la certificacion 2026-08-13), y reactivacion de la IA en una sala nueva
  tras cerrar un ticket (nunca antes probado).

Verificado: `docker compose exec sintel_ai pytest tests -v` → 134 passed, 16 skipped (subio de
117 el 2026-08-08); `docker compose exec django pytest support/tests.py notifications/tests.py -v`
→ 67 passed (subio de 60). Commit `59aea7f` en `fix/audit-p0-remediation`. Detalle completo,
con tabla de correcciones archivo-por-archivo: `ai_engine/.AGENT/SUPPORT_AI_CERTIFICATION.md`
("Historial de correcciones (2026-08-17)").

**No incluido en este cierre** (fuera del alcance pedido — "cerrar gaps conocidos", no
re-auditoria completa): pruebas E2E multi-Customer con navegador real simultaneo,
carga/concurrencia contra Ollama real bajo `AI_SUPPORT_CHAT_ENABLED=True` en un entorno
productivo (produccion hoy no corre `sintel_ai`), y el gap ya documentado de WhatsApp con
`conversation_id` en namespace separado del canal web (`wa-{user_id}` vs `room-{uuid}` —
deliberadamente pospuesto, ver `AUDITORIA/19_AUDITORIA_COMMUNICATION_CENTER_CANALES.md`).

### En progreso (2026-08-14 — Migracion a autoridad unica de tecnico)
- **Regla oficial adoptada**: `technical_services.ServiceOperation.technician`
  es la unica fuente de verdad (SOURCE OF TRUTH) para "que tecnico esta
  asignado a un servicio". `orders.OrderServiceDetail.technician` queda
  declarado LEGACY/COMPATIBILITY -- no debe aceptar cambios independientes.
- **FASE 0 (auditoria, completa)**: 3 vias de escritura activas encontradas
  al campo legacy -- 2 endpoints de `orders/service-orders/` (usados por
  `TechnicianAssignmentBoard.vue`) + **el Django Admin nativo** (`/admin/`),
  esta ultima sin pasar por ningun Command (sin validar disponibilidad, sin
  liberar al tecnico anterior, sin timeline, sin notificacion).
- **FASE 1 (completa)**: cerrado el hallazgo mas riesgoso -- `technician` ahora
  es `readonly` en `OrderServiceDetailAdmin` (Django Admin nativo ya no
  puede escribirlo).
- **FASE 2-4 (completa)**: `ServiceOperationCommands.assign_technician()`/
  `unassign_technician()` es ahora el unico lugar que decide una asignacion real
  (precondicion de fecha relajada -- decision explicita del usuario via
  `AskUserQuestion` para no romper el flujo existente del panel legacy de Orders,
  que nunca exigio planeacion previa -- y `TechnicianProfile.is_available` ahora
  tambien se sincroniza desde aqui, segundo hallazgo real encontrado durante esta
  fase). `orders/service-orders/assign-technician|auto-assign|unassign-technician`
  ya no deciden nada por su cuenta -- delegan integramente y solo escriben
  `OrderServiceDetail.technician` como snapshot de compatibilidad. Serializers de
  ambos paneles (`OrderServiceDetailSerializer`, `ServiceAssignmentQueueSerializer`)
  actualizados para leer la fuente real primero. Regresion completa verificada:
  `technical_services` + `orders` + `dashboard`, 271 tests, OK. Detalle completo en
  `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` §23.
- **FASE 6-9 (completa)**: `ServiceTechnicianReconciliationSelector` (lectura
  sancionada + auditoria de divergencia) corrido contra la base de datos real --
  **0 conflictos reales** entre los 2 sistemas. 8 divergencias encontradas, todas
  benignas y explicadas (3 asignaciones nuevas esperadas, 5 ordenes historicas
  `pending` de antes de que `ServiceOperation` existiera). Reporte completo en
  `technical_services/.AGENT/TECHNICIAN_ASSIGNMENT_RECONCILIATION_REPORT.md`. 2
  lectores adicionales del snapshot legacy cerrados (notificacion de pago
  confirmado al cliente, columna del admin nativo).
- **Decision FASE 10-13 (explicita del usuario)**: `TechnicianAssignmentBoard.vue`
  (panel legacy de Orders) se deja tal cual -- ya delega correctamente desde
  FASE 4, quitarle los botones de asignar solo reduciria capacidad de los admins
  sin cerrar ningun riesgo tecnico adicional. Migracion de autoridad de escritura
  (lo que importaba) cerrada.
- **Pendiente, sin decision tomada**: auditoria permanente automatizada, apagar
  escritura legacy del campo, deprecar formalmente. Ver
  `technical_services/.AGENT/TECHNICIAN_ASSIGNMENT_MIGRATION_FASE0_2026-08-14.md`
  para el plan completo de 22 fases y el estado exacto de cada una.

### Completadas (2026-08-14 — Fachada Administrativa Unificada de Technical Services)
- **`/panel/servicios/solicitudes`** (nuevo): primera vista admin que muestra la
  solicitud de servicio ANTES de convertirse en operacion -- no existia equivalente
  (a diferencia de Renting, que ya tenia `/panel/renta/solicitudes`).
- **Fachada, no dominio nuevo**: `orders.Order` sigue siendo el dueno de la
  solicitud comercial, `technical_services.ServiceOperation` sigue siendo el dueno
  del estado operativo. `dashboard.ServiceAdminRequestSelector`/
  `ServiceAdminRequestOrchestrator` (`dashboard/services/admin_orchestrators.py`)
  combinan ambos para lectura; toda escritura delega a `ServiceOperationCommands`
  ya existente. **No se creo ningun modelo `ServiceRequest`.**
- **Hallazgo de auditoria (no un bug introducido, preexistente)**: coexisten HOY
  dos sistemas de asignacion de tecnico sin sincronizar
  (`ServiceOperation.technician` vs. `OrderServiceDetail.technician` legacy,
  usados por dos paneles admin distintos ya existentes). La fachada trata al
  primero como fuente de verdad para escritura y expone el segundo solo como
  lectura con flag `diverges`.
- Endpoint `dashboard/technical-services/requests/` (list/detail +
  plan/assign/schedule/notify/cancel) — sin `/approve/`: el backend de servicios
  no tiene gate de aprobacion tipo `pending_validation` (a diferencia de Renting).
- Frontend: `ServiceRequestsPanel.vue` + `ServiceRequestActionsPanel.vue` +
  store `technicalServicesAdmin/requests.js`, mismo patron UX que
  `RentingRequestList.vue`. KPIs extienden aditivamente
  `ServiceOperationSelector.dashboard_metrics()` (ya existente) -- sin modelo de
  estadisticas nuevo.
- 5 tests nuevos (`dashboard/tests.py::ServiceAdminRequestFacadeTestCase`) +
  regresion completa `dashboard` 57/57 PASS + verificacion manual en navegador
  real (cadena planificar->asignar->notificar, cruzada con `/panel/ordenes/{uuid}`
  y sin regresion en `/panel/renta/solicitudes`).
- Detalle completo: `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md`
  §22, `technical_services/.AGENT/SERVICES_ADMIN_FACADE_BASELINE.md` (auditoria),
  `SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md`,
  `SERVICES_ADMIN_FACADE_FASE2_5_2026-08-14.md`,
  `SERVICES_ADMIN_FACADE_FASE6_14_2026-08-14.md`.
- **No cubierto en este incremento**: `ServiceSelector.get_by_uuid()` (usado por
  el detalle publico de servicios, modulo distinto) no filtra `is_active` --
  hallazgo de una auditoria previa el mismo dia (FASE 7 del rediseno de
  ServiceForm), reportado pero no corregido por requerir separar el selector
  publico del admin.

### Completadas (2026-08-10 — v12, auditoria cruzada AUDITORIA/29-33 + backlog 31-32)
- **`/api/v1/health/` devolvia 200 incondicionalmente** (AUDITORIA/29 P1-CRITICO): `health_check`
  en `ecommerce/urls.py` nunca verificaba nada; `SecuritySelector.get_health_snapshot()` existia
  y era correcto pero solo estaba expuesto detras de auth admin. Corregido: `health_check` ahora
  reusa ese selector y devuelve 503 si db o redis no son alcanzables desde Django especificamente
  (distinto al healthcheck del contenedor de Postgres/Redis, que solo verifica que el proceso
  este vivo). 4 tests nuevos.
- **Formato de logs** (AUDITORIA/29 P2): `{module}` -> `{name}` en `LOGGING` de settings — 9 apps
  distintas tenian `tasks.py`/`views.py` indistinguibles en los logs crudos de produccion.
- **`celery_beat` sin ningun HEALTHCHECK** (AUDITORIA/31): agregado `grep -a -l celery /proc/...`
  — `celery beat` no responde a `inspect ping` (solo para workers), se lee `/proc` con `grep`.
- **Indices de BD** (AUDITORIA/31): `NotificationLog` gano `Index(template_slug)` +
  `GinIndex(payload_context)` (4 scanners proactivos filtraban sin indice en tabla que solo crece);
  `ChatRoom` gano indice compuesto `(status, ai_paused, updated_at, is_deleted)`.
- **Heartbeat WS** (AUDITORIA/31): ping/pong de aplicacion cada 25s en
  `SupportChatWidget.vue`/`SupportDashboardView.vue` + `support/consumers.py`; cierre y reconnect
  automatico si no llega `pong` en 10s. 1 test nuevo.
- **Mensajes proactivos de IA respetan preferencias** (AUDITORIA/32):
  `ai_proactive_room_message_task` ahora verifica `UserNotificationPreference` antes de crear
  el mensaje en la sala (opt-out, mismo criterio que el resto de `dispatch_notification`). 3 tests
  nuevos.
- **`OperationTicketSelector` -> `OperationSelector`** (AUDITORIA/32): nombre de clase inexistente
  corregido en `operations/models.py`, `operations/api/serializers.py` y doc de arquitectura.
- **`CHANNEL_LAYERS` con `capacity`/`expiry` explicitos** (AUDITORIA/32): defaults de
  `channels_redis` eran silenciosos; declarado `capacity=1000`/`expiry=60` explicitamente.
- **Backup automatizado corregido** (AUDITORIA/33 P1-01): tarea Windows Scheduler corria como
  `SYSTEM` (sin acceso al named pipe de Docker Desktop); reinstalada como `Administrator`.
  `backup.sh` ahora valida el dump con `pg_restore --list` y el media con `tar -tzf` antes de
  publicar; `restore.sh` crea snapshot preventivo previo a sobrescribir datos. Verificado
  end-to-end: dump + media generados, restauracion completa, Django `healthy` post-restauracion.
- **Reinicio autorizado de cuentas de produccion** (2026-08-04): borrado logico de 3 cuentas;
  1 cuenta admin restaurada manualmente; contenedor `sintel_prod_django` permanecio `healthy`.
- **2 modulos nuevos documentados**: `sms_bridge` y `project_knowledge_graph` (nunca aparecian
  en ninguna version anterior de este documento pese a existir en el codigo; ver secciones
  dedicadas arriba y en la tabla de apps).

### Completadas (2026-08-10 — v13, auditoria E2E del chatbot + rediseno "Site Knowledge Graph" FASE 0-2)
- **CRITICO — chatbot de soporte sin responder, causa raiz real encontrada por auditoria E2E
  en vivo (no asumida).** El contenedor `frontend` llevaba 18h en `Exited(1)` por
  `Error: EIO: i/o error, stat '/app'` (inestabilidad conocida de bind-mount de Docker Desktop
  en Windows + chokidar, ya mitigada parcialmente con `CHOKIDAR_USEPOLLING=true` en una sesion
  anterior) sin ninguna politica de `restart` que lo recuperara. Se verifico primero, con
  evidencia real (logs `[WS]`/`[CHAT]`/`[AI_BRIDGE]` de Django, no solo lectura de codigo), que
  toda la cadena backend (WebSocket, JWT, `SupportChatConsumer`, `ai_bridge.py`) funcionaba
  correctamente — el problema era exclusivamente que el frontend nunca llegaba a servir la SPA.
  Corregido agregando `restart: unless-stopped` al servicio `frontend` en `docker-compose.yml` y
  recreando el contenedor; verificado `healthy` con `docker inspect`.
- **FASE 0 — desacoplamiento total de `ai_engine` respecto a `project_knowledge_graph`.** Nueva
  regla arquitectonica: "AI Engine no conoce ni importa `project_knowledge_graph`" (y viceversa),
  como preparacion para que `project_knowledge_graph` evolucione en un "Site Knowledge Graph"
  independiente, consumido en el futuro por un "AI Editor Runtime" separado del chatbot. Se
  elimino `ai_engine/tools/graph_tools.py` (`GraphImpactAnalysisTool`) y `ai_engine/
  pkg_bootstrap.py` por completo; se retiraron todos los imports de `project_knowledge_graph`
  en `main.py`, `planner.py`, `graph.py`, `incremental_updater.py` (reemplazados por stubs
  locales que degradan sin romper, no por shims que simulen el modulo ausente); se retiro
  la capacidad `analizar_impacto_arquitectura` y el intent `architecture_impact` de
  `capabilities/registry.py`, `action_graph.py` y `agents/profiles/admin_agent.yaml`. Nuevo
  test `test_pkg_decoupling.py` que hace AST-walk de todo `ai_engine/` y falla si algun archivo
  vuelve a importar `project_knowledge_graph`. Detalle completo (matriz de imports, que
  funcionalidad se perdio y donde debe reubicarse) en `ai_engine/.AGENT/
  AI_ENGINE_KG_DECOUPLING_FASE0.md`. Limitacion documentada, no oculta: `memory_builder.py`/
  `ai_manifest.py`/`specialized_retrieval.py` siguen leyendo `ai_engine/PROJECT_MAP.json`, que
  ya nadie regenera — ver tarea pendiente arriba.
- **FASE 1 — nodos `File` y `Symbol` en el Knowledge Graph.** El grafo estructural de
  `project_knowledge_graph` ahora modela archivos individuales y sus funciones/metodos como
  nodos propios (con rango exacto de lineas via `ast.end_lineno`), enlazados por una nueva
  arista `CONTAINS` (File->Symbol y Clase->su propio metodo), en vez de solo saber que una
  clase "existe" en algun archivo. Objetivo explicito: que una IA futura pueda recibir
  `Clase.metodo() lineas N-M` en vez de solo el nombre del archivo.
- **FASE 2 — "Contract Graph" (WebSocketRoute, EnvVar, `IMPLEMENTED_BY`, `USES_ENV`).** Cada
  `Endpoint` ahora enlaza `IMPLEMENTED_BY` al `Symbol` (metodo de vista) real que lo implementa;
  cada ruta WebSocket de Channels (`routing.py`, `path()`/`re_path()` con `.as_asgi()`) se
  modela como nodo `WebSocketRoute` enlazado `IMPLEMENTED_BY` a su `Consumer`; cada variable de
  entorno leida via `config()`/`env()` (patron real del proyecto, `python-decouple`) se modela
  como nodo `EnvVar` enlazado `USES_ENV` desde el `File` que la lee. 2 bugs reales del propio
  scanner encontrados y corregidos contra el repo real (no fixtures sinteticos): el scanner de
  rutas WebSocket solo reconocia `path()` y perdia `operations/routing.py` (usa `re_path()`);
  y agregaba una entrada aunque el segundo argumento no fuera literalmente `.as_asgi()`. Grafo
  resultante: 6932 nodos / 10833 aristas. 40/40 tests pasando (7 nuevos de esta fase). Detalle
  completo en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md`.

### Completadas (2026-08-11 — v14, cierre completo del rediseno "Site Knowledge Graph -> Change Intelligence -> AI Editor Runtime", FASES 3-21)

Detalle fase por fase (bugs reales encontrados y corregidos en cada una, cifras de grafo
antes/despues, tests) en `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion
11 y en el reporte de cierre `project_knowledge_graph/.AGENT/SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md`.
Resumen por bloque:

- **FASES 3-9 — grafo estructural completo.** `Symbol` extendido a Vue/JS con extraccion
  heuristica regex (Fase 3); Contract Graph frontend<->backend a nivel de simbolo individual —
  corrigio 2 bugs reales preexistentes que nunca se habian notado: `USES_STORE` tenia 0 aristas
  en TODO el grafo (matching por substring sin relacion textual garantizada) y la capa de "custom
  API wrapper" del frontend (69 llamadas reales) era invisible (Fase 4); Data Flow Graph —
  `READS_FROM`/`WRITES_TO` de `Model.objects.verbo()` real, atribuido por `qualified_name` para
  no confundir metodos homonimos entre clases (Fase 5); Execution Graph — `TRIGGERS`/`QUEUES` de
  signals y Celery tasks, corrigio un bug preexistente donde `@shared_task(bind=True, ...)` (el
  patron dominante real de `notifications/tasks.py`) nunca se detectaba como tarea (Fase 6); Test
  Graph — `TESTS`/`VALIDATES`, deteccion real de que tests cubren que codigo (Fase 7);
  Documentation Graph — `REFERENCES` desde texto libre con scoring de relevancia (Fase 8);
  Configuration/Infrastructure Graph — Docker/nginx/env, corrigio un bug real en el parser de
  nginx que matcheaba "location" como substring de "geolocation=()" en un header CSP real (Fase 9).
- **FASES 10-13 — capa de consulta para asistir cambios reales.** `calculate_change_impact()`
  (impacto directo/indirecto categorizado + riesgo heuristico, distinguiendo aristas
  estructurales de funcionales — sin esto, cambiar un metodo de un ViewSet inflaba el impacto de
  42 a 797 nodos "afectados" solo por contener su propia clase); `resolve_change()` (envelope
  completo: archivos/simbolos/contratos/tests/docs/riesgo/orden recomendado); `build_graph_
  context_packet()` (comprime miles de nodos a decenas relevantes para un LLM — verificado real:
  9575 -> 20 para un cambio tipico); `graph_sdk` (fachada estable de 13 operaciones, sin
  reimplementar logica).
- **FASE 14 — `ai_editor/` (decision de seguridad deliberada, NO funcional mas alla de lectura).**
  Paquete nuevo `ecommerce_sintel/ai_editor/` con 7 submodulos; solo `graph_client/` (wrapper de
  solo lectura sobre `graph_sdk`) tiene codigo real. Generar y aplicar modificaciones automaticas
  a archivos de codigo (`patch/`) se dejo **deliberadamente sin implementar** — es una accion
  dificil de revertir con blast radius sobre todo el repositorio, requiere una decision humana
  explicita y separada, no es consecuencia implicita de este rediseno.
- **FASES 15-18 — deteccion, validacion y observabilidad de cambios.** Deteccion symbol-level de
  cambios via `git diff -U0` real (Fase 15, corrigio un bug real de codificacion: `subprocess.run`
  sin `encoding="utf-8"` explicito crasheaba en Windows contra comentarios en español); Change
  Validation Report — compone deteccion + impacto + validador en un reporte real de que cambio,
  que se rompe, que tests correr (sin auto-ejecutarlos, ya que muchos requieren Docker/DB no
  disponibles desde el host) y consistencia de grafo/contratos (Fase 16); diseno documentado
  (sin codigo ejecutable) del Autonomous Change Loop, mismo criterio de seguridad que Fase 14 —
  un loop que aplique patches automaticamente escala el mismo riesgo, no lo separa (Fase 17);
  auditoria real de consultas via `graph_sdk` (operacion/args/resumen del resultado/version del
  grafo), nunca persiste `meta` de nodo ni ningun dato potencialmente sensible (Fase 18).
- **FASES 19-21 — consolidacion, limpieza y validacion final.** 5 defectos reales de
  documentacion encontrados y corregidos en `ARQUITECTURA_COMPLETA_GRAFO.md` (funciones de
  scanner desactualizadas, afirmacion falsa de que pytest no corre en el host, referencia a un
  archivo ya borrado — Fase 19); busqueda en TODO el repo de referencias a los 9 modulos de
  `ai_engine` retirados — 0 bugs de codigo real, pero 4 documentos VIVOS en `ai_engine/.AGENT/`
  (la referencia que `CLAUDE.md` manda leer antes de tocar `ai_engine`) presentaban comandos y
  excepciones ya retiradas como si siguieran vigentes, corregidos con banners de retiro
  explicitos (Fase 20); rebuild completo real (~2 min, 9575 nodos/20335 aristas, identico a lo
  documentado en cada fase, sin drift) + suite de 120 tests corrida dos veces, 0 regresiones
  (Fase 21).
- **Regla 1 del plan verificada, no asumida**: `project_knowledge_graph` sigue sin importar
  `ai_engine` en ninguna direccion durante las 19 fases de codigo — confirmado por test
  automatizado (`test_ai_engine_does_not_import_this_module`), no solo por convencion.

### Completadas (2026-07-29 — 3 incidentes reales encontrados y corregidos en vivo, no una pasada programada)
- **CRITICO — Django no arrancaba en Docker.** `renting/services/presenters.py:14` importaba
  `truncate_words` de `django.utils.text` (funcion que no existe en Django 5); el `ImportError` se
  propagaba via `marketing.services.selectors` -> `internal_ai_urls.py` -> `ecommerce/urls.py`,
  tumbando el URLconf raiz completo. `ecommerce_sintel_django` quedaba `unhealthy`, bloqueando
  `celery_worker`/`celery_beat`/`nginx` (`depends_on: condition: service_healthy`). Corregido con
  `Truncator(...).words(n, truncate=' ...')` en los 2 usos reales. Verificado con
  `docker compose up -d --build django` -> `healthy` en ~20s, luego los 3 servicios dependientes
  arrancaron sin bloqueo. Ver seccion `renting`.
- **Imagenes de equipos/productos no cargaban en `/alquiler`.** `EquipmentHorizontalCard.vue` e
  `ItemCard.vue` (este ultimo compartido con Shop) leian una propiedad plana `equipment.image`/
  `item.image` que el backend nunca devuelve — el contrato real siempre fue `images` (array).
  Corregido con un computed que toma la imagen `is_primary` o la primera del array, en ambos
  componentes. Ver seccion Frontend > "Design System".
- **Cards de catalogo cambiaban de tamaño segun la orientacion de la imagen.**
  `BaseHorizontalCard.vue` (compartido Renting/Services/Shop) usaba `height: 100%` en el wrapper
  de imagen sin que ningun ancestro tuviera altura explicita, dejando que el aspect ratio
  intrinseco de cada `<img>` determinara la altura de toda la card. Corregido con altura fija.
  Ver seccion Frontend > "Design System".
- Alcance explicitamente NO cubierto en esta pasada: no se repitio la verificacion de las 19 apps
  (eso sigue siendo v10, 2026-07-23); no se actualizaron los docs de Nivel 2 propios de `renting`
  ni de `frontend` (ver "Tareas pendientes" arriba).

### Completadas (2026-07-23 — verificacion linea-por-linea contra codigo real, 5 pasadas paralelas)
- Verificados contra codigo real (no solo referenciados): `payment`, `technical_services`,
  `quotes`, `shop`, `inventory`, `cart`, `orders`, `renting`, `marketing`, `core`,
  `notifications`, `operations`, `support`, `dashboard` (tabla de endpoints), RBAC/`accounts`/
  `kyc`/`users`/`organization`/`security`, rutas API raiz (`ecommerce/urls.py`), Frontend
  (estructura/rutas/Design System), Docker infra, variables `.env`.
- 8 discrepancias reales encontradas y corregidas (ver nota de version arriba): ruta REST de
  `support` que el documento negaba explicitamente (la mas relevante — cambia una afirmacion
  arquitectonica, no solo un detalle), signal de `TechnicianProfile`, endpoint de inventario
  `movements/` vs `transactions/`, permiso de `WishlistViewSet`, conteo de modelos de `core`
  (9 -> 12), `/api/v1/dashboard/users/` inexistente, estructura frontend (`apps/customer/` no
  existe, Vite no es multi-entry), variables `.env` (`SECRET_KEY`, `JWT_SECRET_KEY`,
  `DATABASE_URL` no usada, `WOMPI_WIDGET_URL` hardcodeada).
- Ademas se completaron 3 tablas de endpoints que estaban incompletas (no incorrectas, solo
  parciales): `accounts` (5 acciones de recuperacion de clave/reenvio no listadas), `users`
  (6 acciones admin no listadas), `inventory` (ruta top-level `transactions/` no listada).
- Confirmado sin discrepancias: `MIGRACION_CORE_V4_DOMINIOS_FASE1-9` y
  `MIGRACION_ORGANIZATION_FASE1` — son registros historicos fechados y auto-consistentes, no
  requieren actualizacion.

### Completadas (2026-07-12 a 2026-07-20 — gaps de documentacion + AI Core + Design System)
- Cerrados 2 gaps reales de documentacion: `organization` (creada 2026-07-12) y `security`
  (creada ~2026-07-09) llevaban desde su creacion sin aparecer en este documento pese a estar
  operativas en produccion.
- Rutas API raiz reescritas completas contra `ecommerce/urls.py` real — la version anterior le
  faltaban 6 rutas reales (`admin-auth/forgot-password-*` x3, `internal/ai-context/`,
  `internal/ai/`, `organization/`, `security`).
- AI Engine documentado por primera vez como algo mas que "generador de codigo" — el AI Core
  (Fases 1-8, 2026-07-16) le agrego un motor conversacional completo (`/chat`, JWT real, Tool
  Registry, Agent Profiles, confirmacion humana para escrituras) usado por soporte web/WhatsApp.
  Detalle en `ai_engine/.AGENT/` (`GUIA_USO.md`/`FLIJO_COMPLETO_IA_ENGINE.md`/
  `PLAN_DE_ACCION_AI_CORE.md`), no repetido aqui.
- Referenciados (sin re-auditar a fondo): rediseno de Auth 5 fases (2026-07-17), aislamiento de
  dominio del panel ADR-001 (2026-07-13), Design System de frontend `components/base/*`
  (2026-07-18/19), modulo "Nosotros" (vive en `core`, 2026-07-19 — filosofia institucional,
  pagina publica `/nosotros`).
- Migracion a integracion API propia con Wompi (2026-07-13, 10 fases) ya estaba referenciada
  desde la v8 — confirmada vigente, no se repite el detalle.

### Completadas (2026-07-06 a 2026-07-09 — SSoT de identidad, KYC, y 3 motores de Operaciones)
- App `kyc` construida desde cero: verificacion de identidad, documentos privados, timeline,
  Habeas Data — ver seccion dedicada arriba.
- SSoT de identidad: registro siempre CUSTOMER instantaneo; upgrade a profesional solo via KYC
  aprobado; cerrado el ultimo hueco real (2026-07-09: admin ya no crea perfiles especializados
  directamente desde `/panel/usuarios`).
- Arquitectura de perfiles: `ProfileResolver`/`ProfileRegistry`, `VendorProfile` eliminado
  (codigo muerto).
- 3 motores de "Operaciones post-pago" (mismo patron FSM): `renting.RentalOperation`,
  `technical_services.ServiceOperation` (+ checkout en modal), `orders.Shipment` extendido
  ("Shop Operations").
- `renting.AvailabilityEngine` (2 fases): el lock de disponibilidad ya no lo dispara
  `pending_payment`, sino la confirmacion real del pago.
- Bug de sincronizacion Wompi corregido (`_sync_wompi_status` exigia un campo que solo poblaba el
  webhook — pagos quedaban "en proceso" para siempre sin el webhook).

### Completadas (2026-07-03, segunda ronda — cierre de pendientes detectados)
- Permisos `renting`: `RentingCategoryViewSet`/`RentingBrandViewSet`/`RentalLaborViewSet` ahora
  declaran `permission_classes = [AllowAny]` explicitamente; las dos primeras ademas dejaron de
  usar los selectores "_for_admin" (exponian items inactivos a usuarios anonimos) — 6 tests
  nuevos en `renting/tests.py` (no existia antes).
- Permisos `marketing`: `MarketingCampaignViewSet`/`AgentRunViewSet`/`DashboardViewSet` ahora
  usan `IsAdminUser` (de `users.api.permissions`); `FlashOfferViewSet` usa `AllowAny` — 6 tests
  nuevos en `marketing/tests.py` (no existia antes).
- `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` reescrito: ya no describe una REST API
  inexistente, documenta el flujo WebSocket real (`ws/support/chat/`) y la gestion admin real via
  `dashboard/api/views.py::AdminSupportChatViewSet`.
- Creado `dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` (no existia) con el
  inventario completo de las 34 ViewSets y los 10 Orchestrators reales.
- `inventory/CLAUDE.md` corregido: ya no menciona `is_available()`/`get_stock_record_for_variant()`
  (no existen); documenta la firma real de `StockAdjustmentDTO`.
- `CLAUDE.md` raiz: agregadas las entradas faltantes de `dashboard`/`operations` a la tabla de
  routing, y corregida la version de Django (decia "Django 4", es "Django 5 / 5.2.13").

### Completadas (2026-07-03, primera ronda)
Ver seccion "Correcciones y mejoras aplicadas (2026-07-03)" arriba — 10 bugs corregidos en 6 apps
distintas, todos derivados del mismo patron de refactor incompleto ("desacoplar de `inventory` via
signal"), mas la sincronizacion completa de RBAC, rutas raiz, dashboard BFF, y la identificacion de
4 apps (`core`, `notifications`, `operations`, `support`) que no aparecian en ninguna version
anterior de este documento.

### Completadas (2026-06-24)
- Integracion del motor de calculo `ServicePricingCalculator` en `ServiceSelector.get_variant_quotation` para cotizaciones dinamicas.
- Ampliacion de la suite de pruebas con `ServiceCostRulePricingTestCase` para verificar reglas de costo globales y especificas de variante.
- Aseguramiento de permisos admin `IsAdminUser` (de `users.api.permissions`) en la gestion administrativa del motor de precios.

### Completadas (2026-06-20)
- `WOMPI_EVENTS_KEY` ya estaba en `.env` — verificacion de firma webhook activa (nombre real: `WOMPI_EVENTS_SECRET`)
- Permisos `renting/api/views.py` migrados a `users.api.permissions.IsAdminUser`
- `technical_services/api/views.py` ya usaba el permiso correcto desde antes
- Upload de imagen/logo en `CategoryForm.vue` y `BrandForm.vue`
- Campos `short_description` y `video_url` en `ProductForm.vue`
- Logistica (`weight`/`length`/`width`/`height`) en variantes del ProductForm
- `ProductDetailView.vue`: fetch correcto por UUID, resumen corto, embed de video, logistica, seccion de resenas con `is_verified_purchase`
- Action `GET /shop/products/<uuid>/reviews/` para listado publico de resenas
