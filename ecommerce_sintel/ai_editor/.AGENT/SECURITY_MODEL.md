# Modelo de seguridad de `ai_editor/`

Consolidado de TODOS los guardrails reales del sistema, con el archivo
donde vive cada uno. Auditado explicitamente en POST-GRAPH 18 (ver
`AI_EDITOR_BASELINE.md` seccion 23 para la tabla de verificacion completa).

## 1. Aislamiento del workspace (`workspace.py`)

- `WORKSPACE_ROOT` calculado de forma independiente (no reusa
  `project_knowledge_graph.config.BASE_DIR`).
- `resolve_workspace_path()`/`resolve_repo_file()` rechazan (`Worksp
  aceViolation`) cualquier path que resuelva fuera de la raiz -- incluye
  `../` y symlinks que escapen (`.resolve()` sigue symlinks ANTES del
  chequeo de boundary, verificado con un symlink real en POST-GRAPH 18).

## 2. Sandbox aislado (`repository/sandbox.py`)

- `create_sandbox(plan)` copia SOLO los archivos que un plan toca, nunca
  el repo completo.
- Nunca copia archivos que matcheen un patron sensible: `.env`, `secret`,
  `credential`, `.pem`, `.key`, `id_rsa`/`id_ed25519`/`id_ecdsa`, `.p12`,
  `.pfx`, `.crt`, `.cer`, `backup`, `.dump`, `.sql.gz`.
- `MAX_SANDBOX_FILES = 500` -- un plan con mas archivos que eso trunca,
  el exceso queda en `files_over_limit`.

## 3. Patch Engine (`patch/engine.py`, `patch/schema.py`)

- `apply_operation(sandbox_root, ...)` -- `sandbox_root` es OBLIGATORIO,
  sin default. Si `sandbox_root == WORKSPACE_ROOT`, se rechaza salvo
  `allow_live_workspace=True` explicito (nadie lo pasa hoy).
- Verifica fingerprint (sha256) del contenido REAL antes de
  MODIFY/DELETE/REPLACE -- aborta si no coincide (el archivo cambio
  desde que se genero el plan).
- `MAX_PATCH_CONTENT_BYTES = 5 MB` -- `PatchOperation` rechaza contenido
  mas grande al construirse.

## 4. Commit Control (`repository/promote.py`) -- el mas protegido

`promote_to_workspace()` es la UNICA funcion de todo `ai_editor` que
puede escribir sobre un checkout real. 4 capas independientes:

1. `ApprovalRecord.decision == APPROVE` real (no un booleano suelto).
2. `confirm=True` explicito ADEMAS de la aprobacion.
3. `workspace_root` argumento obligatorio, sin default.
4. Re-verificacion de fingerprint de CADA archivo contra el estado real
   del destino, todo-o-nada (aborta completo si algo cambio).
5. **[POST-GRAPH 20]** Si se pasa `validation_report` y `level_1_passed`
   es `False`, rechaza ESTRUCTURALMENTE -- sin importar la aprobacion
   humana. Gap real encontrado auditando el invariante "Patch NO se
   promociona si la validacion falla": antes de esto, nada en codigo
   impedia promover un cambio con sintaxis rota si un humano lo aprobaba
   por error.

**Esta sesion nunca invoco `promote_to_workspace()` contra
`WORKSPACE_ROOT` real** -- solo contra directorios/repos git temporales.

## 5. Commit git (`repository/promote.py::commit_changes()`)

`git add` + `git commit` LOCAL como maximo. Nunca `git push`, nunca
deploy, nunca reinicia servicios (verificado: el repo de prueba usado en
tests no tiene ningun remoto configurado).

## 6. Auditoria sin fuga de secretos (`audit/log.py`)

`log_change_operation()` sanitiza CUALQUIER clave que matchee
`secret`/`password`/`token`/`api_key`/`credential`, en el nivel raiz Y en
dicts anidados (bug real de sanitizacion parcial encontrado y corregido
en POST-GRAPH 13 -- ver `AI_EDITOR_BASELINE.md` seccion 19). Valores de
texto largos se truncan a 500 caracteres.

## 7. Cliente LLM (`llm/providers.py`)

Nunca loguea `api_key` -- ni en el flujo normal ni en mensajes de error
HTTP (verificado con un test que simula un 401 y confirma que la key no
aparece en la excepcion).

## 8. Lo que sigue sin resolver (documentado, no un gap oculto)

- El sandbox parcial no permite ejecutar tests reales ni reconstruir el
  grafo -- decision explicita del usuario de mantenerlo asi por ahora
  (ver "Fork del sandbox", `MEMORY.md`/`AI_EDITOR_BASELINE.md`).
- No hay generacion de codigo real -- por lo tanto, Graph Reconciliation
  (POST-GRAPH 9) tampoco tiene un escenario real que cubrir todavia.

## 9. Security impact gate (HARDENING F22, 2026-09-25)

`approval/security_gate.py` clasifica, por patrones de ruta (determinista, sin LLM), los archivos de un cambio que tocan superficies de seguridad:
config de produccion (compose prod, nginx prod, `deploy/`), autenticacion/autorizacion, politicas de Tools, kill switches y endpoints de modelo,
RAG, memoria, backups, la propia frontera del editor (`approval/`, `repository/`, `patch/`) y las guardias de entrada/salida del asistente.

- `ChangeSummary.security_review_required` / `security_categories` y una linea `SECURITY_REVIEW_REQUIRED` en `render_text()`.
- `promote_to_workspace()` devuelve `SECURITY_REVIEW_REQUIRED` (sin escribir nada) salvo que el `ApprovalRecord` lleve
  `security_review_acknowledged=True` (`record_decision(..., security_review_acknowledged=True)`), ademas de APPROVE y `confirm=True`.
- Los secretos (`.env`, claves, certificados) siguen bloqueados por completo por `sandbox._SENSITIVE_PATTERNS` (nunca se promueven).
- Tests escritos, no ejecutados: `approval/tests_security_gate.py`.
- Lista de rutas: `SECURITY_PATH_RULES`; ampliarla en el mismo cambio que agregue una superficie nueva.
