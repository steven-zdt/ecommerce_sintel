# CODE_CONTROL_PLANE - plano de codigo del MCP

Estado (2026-09-25): **lectura + analisis por grafo + propuestas en sandbox + promocion/rollback con aprobacion humana**, SOLO DESARROLLO (`AI_EDITOR_CODE_PLANE_ENABLED`, apagado por defecto). La escritura de codigo NO existe en el MCP y **siempre** debera pasar por `ai_editor` (pipeline READ -> RESOLVE -> PLAN -> PROPOSE -> SANDBOX -> VALIDATE -> APPROVAL -> PROMOTE -> ROLLBACK). No se crea un editor paralelo.

## Hallazgo de arquitectura (Fase 0) que condiciona la integracion con `ai_editor`
`ai_editor` es un paquete del propio repo de Django que opera sobre el **workspace real** (`ai_editor/workspace.py::WORKSPACE_ROOT`) y su `promote_to_workspace()` escribe en el checkout. En los contenedores de
produccion el codigo es la copia dentro de la imagen, **no** el repo git: promover alli editaria archivos del contenedor sin llegar a git y se perderia al recrear. Por eso:
1. El plano de codigo con escritura (propose/validate/promote/rollback) debe ejecutarse **solo donde vive el checkout** (desarrollo / la maquina del repo), con el workspace montado de forma controlada.
2. El MCP de produccion debe limitarse al plano API (CRUD/lectura) y, como maximo, lectura de codigo de la imagen.
3. La promocion a produccion sigue siendo el flujo sancionado (`deploy/deploy.sh`) tras aprobacion humana; el MCP no despliega.
`ai_editor` ya exige `ApprovalRecord(APPROVE)` + `confirm=True` + fingerprints sin drift, y (F22) `security_review_acknowledged=True` para superficies de seguridad (`ai_editor/approval/security_gate.py`). El MCP no puede saltarse ninguno.

## Lo implementado (lectura)
Ver SECURITY_MODEL.md sec. 7. Limites: 64 KB por lectura, 50 coincidencias, 5000 archivos por busqueda, sin regex del usuario, extensiones de texto, secretos enmascarados, rutas sensibles bloqueadas, sin symlinks.

## Implementado (Fase 7-8): el MCP como adaptador de `ai_editor` via Django
El MCP NO importa `ai_editor` ni toca el repo: llama a `/api/v1/dashboard/code/...` (Django, `dashboard/api/code_plane_views.py`), que reusa `ai_editor` sin reimplementarlo. Apagado por defecto
(`AI_EDITOR_CODE_PLANE_ENABLED=false`; 404 `CODE_PLANE_DISABLED`); `.env` de desarrollo lo enciende y `.env.production` lo deja en `false` (el codigo de produccion es una copia de la imagen, no un repo).

| Tool MCP | Clase | Perfil minimo | Endpoint Django | Notas |
|---|---|---|---|---|
| `code.graph_status`, `code.describe_symbol`, `code.find_references`, `code.impact_analysis`, `code.resolve_change`, `code.build_context`, `code.find_tests` | READ | CODE_REVIEW | `GET code/analysis/?op=...&q=...` | `ai_editor.graph_client` (solo lectura); `find_tests` NO ejecuta tests |
| `code.list_changes`, `code.change_status` | READ | CODE_REVIEW | `GET code/proposals/[id]/` | estado, compuerta, reportes de validacion/riesgo/impacto, `required_tests`, aprobacion |
| `code.propose_change` | WRITE | CODE_CHANGE | `POST code/proposals/` | `run_autonomous_change_loop()` (LLM de ai_editor); sandbox, NUNCA escribe el repo; max 2000 caracteres |
| `code.promote_change` | DESTRUCTIVE | CODE_CHANGE | `POST code/proposals/<id>/promote/` | exige `confirm=true` + aprobacion humana previa; `promote_to_workspace()` (5 compuertas + F22 + deriva) |
| `code.rollback_change` | DESTRUCTIVE | CODE_CHANGE | `POST code/proposals/<id>/rollback/` | `rollback_promotion()` con los `files_before` del proceso |
| `code.discard_change` | WRITE | CODE_CHANGE | `DELETE code/proposals/<id>/` | limpia el sandbox |

**No existe Tool de aprobacion.** `POST code/proposals/<id>/decision/` solo acepta a un admin con sesion normal: un JWT con `via=mcp` recibe 403 (y queda auditado `code_decision_denied`).
El humano decide con `security_review_acknowledged` cuando el cambio toca superficies de seguridad (F22).
`validate_change` = el detalle (`code.change_status`): el loop ya valido sintaxis, arquitectura, contratos, dependencias, tests, documentacion, reconciliacion e impacto antes de dejar la propuesta en `APPROVAL_REQUIRED`.
`run_tests` NO se implementa a proposito (regla del proyecto: los tests los corre una persona): `required_tests` lista `tests_to_update/tests_to_add` y los del plan.

### Ciclo completo
`code.impact_analysis` -> `code.propose_change` -> (humano revisa en el panel/API: `GET code/proposals/<id>/`, `POST .../decision/ {decision: APPROVE}`) -> tests manuales -> `code.promote_change(confirm=true)` -> (si algo falla) `code.rollback_change(confirm=true)`.

### Limites conocidos
- El almacen de propuestas es **en memoria del proceso Django** (`ai_editor/change_store.py`, TTL 2 h, max 20): el sandbox vive en un directorio temporal de ese proceso. Reiniciar Django pierde las propuestas (se regeneran). Un solo worker en desarrollo (daphne).
- `propose_change` depende del LLM de `ai_editor` (`AI_EDITOR_LLM_PROVIDER`, Ollama por defecto). Sin modelo alcanzable devuelve `state=FAILED` con el motivo, sin efectos. Ollama esta deshabilitado como proveedor de chat; el loop del editor es independiente y hay que apuntarlo a un LLM disponible antes de usarlo de verdad.
- El rollback solo funciona mientras el proceso conserve la promocion (`files_before` en memoria); despues, `git`.
- Produccion: plano apagado y sin decision de despliegue; el despliegue sigue siendo `deploy/deploy.sh`.

### Verificacion (2026-09-25, dev)
Django (script funcional, 16 + 13 comprobaciones): analisis, 400/403/401, `via=mcp` no aprueba, promocion sin aprobar rechazada, sin `confirm` 409, deriva de workspace 409, promocion real de un archivo de prueba y rollback restaurado, auditoria `code_*`.
MCP real (fase `code` del smoke, 17 comprobaciones) y regresion `readonly` + `write` sin fallos. La propuesta con LLM real no se pudo completar porque el proveedor de `ai_editor` (Ollama) no esta disponible: solo se verifico el camino de fallo limpio.
