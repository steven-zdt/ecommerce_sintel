# CODE_CONTROL_PLANE - plano de codigo del MCP

Estado: **solo lectura implementada** (`code.search`, `code.read`). La escritura de codigo NO existe en el MCP y **siempre** debera pasar por `ai_editor` (pipeline READ -> RESOLVE -> PLAN -> PROPOSE -> SANDBOX -> VALIDATE -> APPROVAL -> PROMOTE -> ROLLBACK). No se crea un editor paralelo.

## Hallazgo de arquitectura (Fase 0) que condiciona la integracion con `ai_editor`
`ai_editor` es un paquete del propio repo de Django que opera sobre el **workspace real** (`ai_editor/workspace.py::WORKSPACE_ROOT`) y su `promote_to_workspace()` escribe en el checkout. En los contenedores de
produccion el codigo es la copia dentro de la imagen, **no** el repo git: promover alli editaria archivos del contenedor sin llegar a git y se perderia al recrear. Por eso:
1. El plano de codigo con escritura (propose/validate/promote/rollback) debe ejecutarse **solo donde vive el checkout** (desarrollo / la maquina del repo), con el workspace montado de forma controlada.
2. El MCP de produccion debe limitarse al plano API (CRUD/lectura) y, como maximo, lectura de codigo de la imagen.
3. La promocion a produccion sigue siendo el flujo sancionado (`deploy/deploy.sh`) tras aprobacion humana; el MCP no despliega.
`ai_editor` ya exige `ApprovalRecord(APPROVE)` + `confirm=True` + fingerprints sin drift, y (F22) `security_review_acknowledged=True` para superficies de seguridad (`ai_editor/approval/security_gate.py`). El MCP no puede saltarse ninguno.

## Lo implementado (lectura)
Ver SECURITY_MODEL.md sec. 7. Limites: 64 KB por lectura, 50 coincidencias, 5000 archivos por busqueda, sin regex del usuario, extensiones de texto, secretos enmascarados, rutas sensibles bloqueadas, sin symlinks.

## Siguiente paso (no hecho)
Montar `ai_editor`+`graph_client` en un runtime de desarrollo del MCP y exponer: `code.describe_symbol`, `find_references`, `impact_analysis`, `resolve_change`, `build_context`, `propose_change`, `validate_change`, `run_tests` (solo tests en sandbox),
`approval_status`, `promote` (solo con `ApprovalRecord` humano), `rollback`. Requiere decidir: contenedor con acceso al repo (dev), como se entrega la aprobacion humana (fuera del canal del LLM) y como se ejecutan los tests sin abrir un shell.
