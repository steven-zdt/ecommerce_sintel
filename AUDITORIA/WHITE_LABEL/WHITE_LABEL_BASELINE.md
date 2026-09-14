# WHITE_LABEL_BASELINE.md
Fase 0 — Baseline técnico (auditoría de viabilidad white-label)

Generado: 2026-08-14. Solo lectura — no se modificó código, modelos, migraciones ni configuración.

## Identificación del repositorio

- **Commit HEAD:** `5a9f642819759206c70e7321c5ce1fae7b6f2adf`
- **Fecha del commit:** 2026-08-07 15:44:45 -0500
- **Branch actual:** `fix/audit-p0-remediation`
- **Branch base:** `main`
- **Working tree:** NO limpio. Hay ~710 líneas de `git status --short` (modificaciones y archivos untracked) correspondientes a trabajo en curso preexistente (migraciones nuevas de `organization`, `quotes`, `renting`, `shop`, `technical_services`, `support`, `security`; refactor de `technical_services` manual pricing; limpieza de `ai_engine/.AGENT` y `AI_MANIFESTS`/`APP_MEMORY`; nueva app `project_knowledge_graph` y `seo` sin trackear). Esta auditoría **no toca ninguno de esos archivos**; se registra el estado tal como se encontró para que un futuro diff no confunda cambios de esta auditoría con el trabajo preexistente.

## Estructura del proyecto

Monorepo con Django (backend, `ecommerce_sintel/ecommerce_sintel/`) + Vue 3/Vite (`frontend/`) + apps auxiliares (`ai_editor/`, `ai_engine/`, `ai_provider/`, `project_knowledge_graph/`). Apps Django relevantes al dominio de negocio:

`accounts, ai_editor, ai_engine, ai_provider, cart, core, dashboard, ecommerce, frontend, inventory, kyc, marketing, notifications, operations, orders, organization, payment, project_knowledge_graph, quotes, renting, security, seo, shared, shop, support, technical_services, users`

## Servicios activos (Docker)

Dos stacks corriendo simultáneamente al momento de la auditoría:

**Dev (`ecommerce_sintel_*`):** celery_worker, celery_beat, django (healthy), ai, nginx, frontend, db (healthy), redis (healthy), chromadb (healthy), ollama — todos Up.

**Prod (`sintel_prod_*`):** celery_beat (healthy), celery_worker (healthy), django (healthy), redis (healthy), db (healthy), cloudflared, nginx (healthy) — todos Up.

Esto confirma que existe un stack de producción real (`sintel_prod_*`) con su propio dominio/branding — relevante para las fases de dominio (Fase 17) y para el riesgo de cualquier migración futura (no debe tocarse durante la migración white-label sin plan de despliegue explícito).

## Documentación canónica — estado real vs. esperado

El prompt maestro asume una estructura de documentos que **no coincide exactamente** con lo que existe en el repo. Se registra como `DOCUMENTATION_DRIFT`:

| Documento esperado por el prompt | Estado real |
|---|---|
| `IMPLEMENTATION_SUMMARY.md` | Existe: `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` (2234 líneas) |
| `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` | **No existe con ese nombre.** `organization/.AGENT/` existe pero sin ese archivo específico (ver hallazgos del agente de Organization) |
| `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` | **No existe con ese nombre** |
| `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` | **No existe con ese nombre** |
| `dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` | **No existe con ese nombre** (hay `dashboard/.AGENT.md` y `dashboard/.AGENT/`) |
| `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` | **Existe tal cual**, última revisión 2026-08-10 |

Regla aplicada: donde la documentación no coincide con el código real, el código real es la fuente de verdad; esta auditoría no corrige la documentación, solo lo registra aquí y en los documentos de hallazgos correspondientes.

## Knowledge Graph

`project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` confirma: módulo independiente de análisis estructural (Django+Vue), última revisión 2026-08-10. Ya está desacoplado de `ai_engine` (ver memoria de sesiones previas: FASE 0 de desacoplamiento completada 2026-08-10). Se usó como fuente de resolución de dependencias donde fue posible; su cobertura real se evalúa en el documento de impacto del grafo.

## Tests / migraciones pendientes

No se ejecutaron `manage.py test` ni `manage.py showmigrations` durante esta auditoría (evitar cualquier efecto secundario sobre una base de datos compartida con el stack Docker activo, incluida potencialmente la de producción). Se recomienda ejecutar ambos manualmente como parte del checkpoint antes de iniciar la Fase 1 de migración real. Existen migraciones nuevas sin commitear (`organization/migrations/0003-0005`, `renting/migrations/0001` squash, `technical_services/migrations/0032-0037`, etc.) — indicio de desarrollo activo simultáneo a esta auditoría.

## AI Editor

`ai_editor/` presente como app independiente; no se investigó en profundidad en esta fase (se cubre en el documento de AI/RAG).

## Alcance de esta auditoría

Se realizó mediante lectura de código, grep dirigido y agentes de investigación en paralelo (sin modificar nada). Dado el tamaño del repositorio, la cobertura de grep de identidad (Fase 1) se hizo sobre patrones específicos definidos en el prompt maestro, no exhaustiva carácter por carácter; se reportan conteos y ejemplos representativos, no cada ocurrencia individual.
