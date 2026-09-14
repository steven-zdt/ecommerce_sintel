# Auditoría real del "INFORME DE VALIDACIÓN — SINTEL AI — Preparación para sintel_prod_ai"

**Fecha de esta auditoría:** 2026-09-14
**Metodo:** cada afirmación del informe externo (22 secciones, fechado "14 de septiembre de
2026") verificada contra el repositorio real -- grep/lectura directa de código, configs y
documentación real, no contra la premisa del informe. Sigue al fact-check inicial (delegado a
un fork durante esta misma sesión) que ya había detectado que la arquitectura multi-tenant
descrita no existe en este proyecto (ver memoria `project_no_multitenant_confirmed`).

**Veredicto global:** el informe mezcla (a) principios generales de seguridad válidos
(OWASP/NIST, como referencia externa, no verificables contra el repo), (b) una arquitectura
multi-tenant ficticia (`AIContext`, `apps/services/ai/`, `AI-VECTOR-06`, aislamiento por
sede/área) que **no existe en este proyecto deliberadamente single-tenant**, y (c) algunos
hallazgos de infraestructura fabricados sin respaldo en ningún archivo real del repo
(discrepancia runserver/Gunicorn, CN de certificado `*.sintel.com`). Dentro de todo eso, el
informe SÍ acierta en 2-3 puntos genuinamente reales, uno de los cuales (el leak de
razonamiento) ya se cerró hoy mismo en esta sesión, antes incluso de recibir este informe.

---

## 1. Veredicto ejecutivo del informe

**Parcialmente desactualizado / parcialmente fabricado.** "AI_ENGINE = NOT_VERIFIED" y
"producción no corre sintel_ai" eran ciertos como snapshot histórico (confirmado en
`Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md:1632-1633`, última edición
2026-08-17: *"produccion **no corre `sintel_ai` en absoluto**"*) -- pero desde HOY
(`AUDITORIA/ADK_CUTOVER_PLAN.md` secciones 4sexies/4septies) esto ya no es cierto: el cutover
a Google ADK está migrado y `AI_SUPPORT_CHAT_ENABLED=True` en producción real. "WRITE
permanece bloqueado estructuralmente" es **falso** incluso en el snapshot histórico -- ver
punto 3.2. "AI-VECTOR-06" es **fabricado**, no existe en ningún documento ni código real.

## 2. "Los dos documentos no representan el mismo estado"

**Parcialmente real, parcialmente fabricado.** Cierto que `IMPLEMENTATION_SUMMARY.md` describe
una arquitectura vieja (previa a hoy). Pero la "arquitectura más reciente" que el informe
describe como reemplazo (`apps/services/ai/ → AIContext → Tool Registry → AI Engine →
PostgreSQL+pgvector`) **tampoco es la arquitectura real** -- ese path no existe
(`find . -path "*apps/services/ai*"` → vacío), y `AIContext` no es una clase real (ver punto
3.3). La arquitectura real actual es `ai_engine_adk/` (Google ADK, migrado HOY, ni mencionado
en el informe) + Django `ai_knowledge` app (pgvector, retirado ChromaDB también HOY, antes de
este informe). El archivo fuente citado
`"arquitectura_general(20260912-130828).md"` **no existe** en el repo -- solo existe el
directorio `Documentacion/Arquitectura_general/` con otros nombres de archivo reales.

## 3. Qué está bien (según el informe)

- **3.1 Aislamiento multi-tenant por schema:** **FABRICADO.** Confirmado dos veces en memoria
  de sesión que el proyecto es single-tenant. No hay `TenantMixin`/`django-tenants`/
  `schema_context` en el repo real.
- **3.2 AI WRITE bloqueado estructuralmente:** **FALSO.** `IMPLEMENTATION_SUMMARY.md:49,77`
  documenta escritura real vía AI ("FASE 54-55, confirmado real contra el repositorio"),
  gateada por confirmación humana ("nunca la primera [capa], solo detrás de aprobación
  humana"), no bloqueada. Confirmado también en código: `action_graph.py::node_execute_write`
  ejecuta escrituras reales tras `policy_decision == "allow"`/confirmación, y
  `sintel_adapter.py` mapea `requires_confirmation` a `FunctionTool(require_confirmation=...)`
  de ADK -- el mismo patrón en ambos runtimes. WRITE existe, gateado, no bloqueado.
- **3.3 AIContext tenant-aware, `AI-01 = VERIFIED`:** **FABRICADO.** `AIContext` no es una
  clase real en ningún módulo Python del repo (`grep "class AIContext"` → vacío). La única
  mención es un comentario en `adk_poc/sintel_root_workflow.py:37` que dice, textualmente, que
  `auth.fetch_user_context` "YA es el 'AIContext' que el plan pedía crear de cero" -- una
  analogía informal en un POC, no un componente ni un gate `AI-01`.
- **3.4 Feature flags server-side:** **Cierto en espíritu, distinto en detalle.** El flag real
  es uno solo, `AI_SUPPORT_CHAT_ENABLED` (`ecommerce/settings/base.py:344`), server-side,
  `config(..., cast=bool)` -- no los nombres `AI_ENABLED`/`AI_READ_ENABLED` que inventa el
  informe, pero el principio (no depende de `request.data`) se cumple igual.
- **3.5 Human Approval del AI Editor:** **CONFIRMADO REAL.** `promote_to_workspace()` existe
  en `ai_editor/repository/promote.py:83`. Guardrails y separación de `ai_editor/agent/`
  verificados en sesiones previas (ver `project_support_agent_separation_plan` memoria).
- **3.6 Rate limiting vía Redis:** **CONFIRMADO REAL** -- y con un hallazgo propio relevante:
  esta misma sesión encontró que este rate limiter existía en el runtime OLD
  (`action_graph.py`, Redis DB2, desde FASE 23 2026-08-17) pero **nunca se había portado al
  runtime ADK** que ya sirve producción real -- gap cerrado hoy mismo
  (`ai_engine/rate_limit.py`, ver `AUDITORIA/ADK_CUTOVER_PLAN.md` sección 4nonies), ANTES de
  recibir este informe.

## 4-5. Bouchard / actualización OWASP

Comentario general sin afirmaciones verificables contra este repo. Válido como referencia de
industria; no se audita como hecho del proyecto.

## 6. Riesgos que el informe pide añadir

- **AI-VECTOR-06 (crítico, según el informe):** **FABRICADO.** No existe ningún gate con ese
  ID, ni el problema que describe (fuga cross-tenant/sede/área) es aplicable -- no hay
  multi-tenancy, sedes ni áreas como conceptos de aislamiento en este proyecto.
- **Public Output Boundary (crítico, según el informe):** **REAL -- y YA CERRADO.** Esta es la
  única sección donde el informe describe con precisión un problema genuino (el leak de
  razonamiento de Qwen3.5, exactamente el mismo que motivó la misión de esta sesión). Ya
  resuelto HOY, ANTES de este informe: `ai_engine_adk/public_response.py`, separación real vía
  `Part.thought` de ADK, filtro defensivo de `<think>`, 11 tests reales, ver
  `AUDITORIA/REASONING_LEAK_FIX_REPORT.md`. La recomendación del informe de NO resolverlo solo
  con `.replace("<think>", "")` es exactamente la restricción dura que ya se siguió.
- **Prompt Injection:** **Guía general válida, gap real no auditado en detalle.** No se
  encontró una suite de tests específica de prompt injection/RAG poisoning en
  `ai_engine/tests/` ni `ai_engine_adk/tests/`. Queda como trabajo futuro genuino, no evaluado
  a fondo en esta pasada (fuera del alcance que el usuario aprobó hoy).
- **Tool Misuse / Excessive Agency:** **Mayormente real, con un gap ya identificado.**
  `ToolMetadata` (`tools/metadata.py`) SÍ declara exactamente los campos que el informe pide:
  `owner`, `risk`, `audit_level`, `rate_limit`, `requires_confirmation`, `timeout_ms`,
  `permissions`. Pero el gate `IsAdminUser` de esos `permissions` **tampoco se portó a ADK**
  (mismo hallazgo de esta sesión, severidad estimada baja porque Django es la autoridad final
  para tools que proxean vía `http_bridge.py`) -- riesgo abierto, documentado, no resuelto
  todavía (ver `ADK_CUTOVER_PLAN.md` 4nonies, "Riesgo pendiente").
- **Secretos (`notas.txt`):** **REAL, confirmado, sigue abierto.** `notas.txt` sigue existiendo
  en la raíz del repo (363 líneas, contiene texto con forma de credencial). Documentado como
  pendiente en `IMPLEMENTATION_SUMMARY.md:1983` ("Rotar credenciales expuestas en `notas.txt`,
  P1-03 de AUDITORIA/33"). **No se rotó en esta sesión** -- requiere decisión explícita del
  usuario sobre qué credenciales y cómo.
- **Backups off-host:** **REAL, confirmado, sigue abierto.**
  `IMPLEMENTATION_SUMMARY.md:1984`: backups hoy en `C:\Users\Administrator\sintel_backups`,
  mismo host que los datos (P2-01 de AUDITORIA/33). No se tocó en esta sesión.
- **Supply Chain:** Guía general razonable. Verificado: `ai_engine/requirements.txt` usa rangos
  (`>=X,<Y`), no `latest` ni pines exactos -- término medio, no una violación dura de la
  recomendación pero tampoco pinning completo.

## 7. "runserver vs Gunicorn"

**FABRICADO.** Cero menciones de `runserver` en ningún archivo de `AUDITORIA/*.md`. El
`Dockerfile` real (`ecommerce_sintel/Dockerfile:110`) define
`CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "ecommerce.asgi:application"]` -- ni siquiera es
Gunicorn (que el informe asume como el destino "correcto"): es **Daphne** (ASGI), la elección
correcta para un proyecto con Django Channels/WebSocket real. No hay discrepancia ni hallazgo
de ningún documento real que respalde esta sección.

## 8. TLS / dominio

**FABRICADO.** Cero menciones de `sintel.com` (sin `.net.co`) o `CN =` en ningún `.conf`,
compose o doc de `AUDITORIA/`. `nginx.prod.conf`/`nginx-common.conf` usan consistentemente
`sintel.net.co`/`www.sintel.net.co`/`api.sintel.net.co`/`panel.sintel.net.co` en todos los
`server_name`. La terminación TLS real es vía Cloudflare Tunnel (`sintel_prod_cloudflared`,
confirmado esta sesión), no un certificado local con CN incorrecto.

## 9. Ollama/Qwen3.5 local primero

**Alineado con la decisión real ya tomada.** Esta sesión, en la misión del leak de
razonamiento, confirmó explícitamente "no fue necesario cambiar Qwen3.5" -- coincide.

## 10-11. Arquitectura recomendada / separación AI Engine vs AI Editor vs EKG

**Directionally correcto, con nombres fabricados en el diagrama.** El PRINCIPIO (separar AI
Engine / AI Editor / Knowledge Graph, Commands como frontera de escritura) es real y ya está
implementado (`project_knowledge_graph_fase0_full_decoupling` memoria: ai_engine importa CERO
código de `project_knowledge_graph`; `Commands` reales en `commands.py` con
`@transaction.atomic`, `IMPLEMENTATION_SUMMARY.md:437`). Pero el diagrama en sí (nombres como
"AI Bridge/API" como módulo formal) no corresponde 1:1 a nombres de archivos reales -- es una
representación aproximada, no una cita de código.

## 12. Evaluación de RAG

**Recomendaciones generales razonables; una cita fabricada.** La mención de que "la capa
`sources.py` ya va en la dirección correcta al utilizar una allowlist" es **falsa** -- no
existe ningún archivo `sources.py` en el repo (`find . -iname sources.py` → vacío). El resto
(tenant/sede/área accuracy) no aplica, ver punto 3.1.

## 13-14. Observabilidad / callbacks-policies

Recomendaciones generales, forward-looking. No son afirmaciones de estado actual verificables;
quedan como referencia útil para trabajo futuro, no como hallazgos de esta auditoría.

## 15. Deployment Docker (no publicar puertos de Ollama/AI Engine)

**YA CUMPLIDO.** Verificado: ni `sintel_ai_adk` ni `sintel_ai` publican `ports:` en
`docker-compose.prod.yml` (0 coincidencias de `ports:` en el bloque de ambos servicios) --
acceso solo por red interna Docker, exactamente como recomienda el informe.

## 16. Health checks

**Parcialmente cumplido.** Existen endpoints de health en `ai_engine/main.py` y
`ai_engine_adk/main.py`. No se verificó en detalle la granularidad completa que pide el informe
(embedding availability, pgvector health por separado) -- posible mejora futura, no un blocker
audita a fondo en esta pasada.

## 17-18. Gates de release / métricas mínimas

Checklist aspiracional razonable como marco de referencia, pero construido sobre el Gate B
(Tenant Isolation) que no aplica a este proyecto (punto 3.1). Los Gates C (Output Boundary) y
parte del D (Tools -- rate limit) SÍ aplican y ya se auditaron/cerraron en esta sesión.

## 19. Tabla "Estado de cada componente"

Ya cubierta fila por fila en los puntos 1-6 de arriba. Resumen: filas de aislamiento
multi-tenant/`AI-VECTOR-06` fabricadas y no aplicables; fila "AI WRITE bloqueado" incorrecta
(es "gateado", no bloqueado); fila "Reasoning/public separation pendiente" **ya cerrada hoy**;
fila "Secrets pendiente" y "Production AI service no verificado" eran reales como snapshot
histórico, la segunda ya se resolvió hoy con la migración a `sintel_production`; filas de
TLS/runserver fabricadas.

## 20-21. Arquitectura final recomendada / decisión sobre Gemma

**21 coincide con la decisión real tomada** (mantener Qwen3.5, no saltar a Gemma). **20**
recomienda un primer release estrictamente `READ-ONLY` -- el proyecto real tomó una decisión
distinta y ya en producción: escritura SÍ habilitada, pero gateada por confirmación humana
(Policy Layer / `requires_confirmation`) en vez de bloqueada del todo. Es una divergencia real
respecto a la recomendación del informe, no un error -- es una decisión de producto ya tomada
y funcionando de forma segura (mismo patrón que Bouchard/OWASP piden: humano en el loop para
alto impacto), documentada, no un gap oculto.

## 22. Conclusión del informe

**Veredicto mixto, ya cubierto arriba.** De los "blockers" que lista la conclusión:
`AI-VECTOR-06` (fabricado, N/A), `TLS/domain discrepancy` (fabricado), `runserver vs Gunicorn`
(fabricado) -- descartados. `Output Boundary` -- **ya cerrado hoy**. `Secret rotation` y
`off-host backups` -- **reales, siguen abiertos**, requieren decisión del usuario.
`Production AI deployment todavía no formalizado` -- **ya resuelto hoy** (migración real a
`sintel_production` + activación). `Agent security controls incompletos` -- parcialmente real:
rate limiting ya portado hoy; `IsAdminUser` gate sigue sin portar (riesgo abierto, documentado).

---

## Resumen ejecutivo de las 22 secciones

| Categoría | Secciones | Conteo |
|---|---|---|
| **Fabricado / no aplica a este proyecto** (arquitectura multi-tenant ficticia) | 1 (parcial), 2 (parcial), 3.1, 3.3, 6 (AI-VECTOR-06), 7, 8, 12 (cita `sources.py`), 19 (filas correspondientes) | ~6 hallazgos concretos fabricados |
| **Real, ya cerrado en esta sesión (antes o durante hoy)** | 6 (Public Output Boundary), 6 (rate limiting de ADK), 1/2/19 (producción AI ya activada) | 3 |
| **Real, sigue abierto -- requiere decisión del usuario** | 6 (secretos `notas.txt`), 6 (backups off-host), 6 (IsAdminUser gate en ADK) | 3 |
| **Ya cumplido, confirmado sin cambios necesarios** | 3.5, 3.6 (base), 9, 11, 15, 21 | 6 |
| **Guía general / recomendación forward-looking, no auditable como hecho** | 4, 5, 6 (prompt injection -- gap real no evaluado a fondo), 10, 13, 14, 16, 17, 18, 20 | resto |

**Las 22 secciones quedan auditadas.** No se declaran "cerradas" en el sentido de "todo
implementado" -- varias son guía general y quedan como referencia, no como pendientes de
código. Los tres hallazgos reales y abiertos (rotación de `notas.txt`, backups off-host, gate
`IsAdminUser` en ADK) quedan documentados explícitamente arriba y en
`AUDITORIA/ADK_CUTOVER_PLAN.md` -- ninguno se tocó sin autorización explícita, siguiendo el
mismo criterio que el resto de esta sesión.
