# Patch Engine (`ai_editor/patch/`)

## Alcance real (leer esto primero)

Implementa el MECANISMO de aplicar un cambio de forma segura. **NO genera
`new_content`** -- eso requeriria una capa de generacion de codigo real
(un LLM escribiendo diffs sobre Django/Vue real), que ninguna fase de
este rediseno construye. `apply_operation()` recibe un `PatchOperation`
ya completo (con `new_content` ya decidido por un humano o un test) y lo
aplica de forma verificable.

## `PatchOperation` (`schema.py`)

```python
PatchOperation(
    file: str,              # relativo, ej. "renting/api/views.py"
    operation: str,          # MODIFY | ADD | DELETE | REPLACE
    line_start: int | None,
    line_end: int | None,
    old_fingerprint: str | None,  # sha256 esperado del contenido actual (None para ADD)
    new_content: str | None,      # None para DELETE
    reason: str,
)
```

Valida `operation` y el tamano de `new_content` (`MAX_PATCH_CONTENT_BYTES
= 5 MB`) en `__post_init__` -- rechaza al CONSTRUIR, no al aplicar.

## Fingerprint (`fingerprint.py`)

```python
compute_fingerprint(text: str) -> str            # sha256 hex
read_lines_fingerprint(path, line_start, line_end) -> str | None  # None si invalido
```

## `apply_operation()` (`engine.py`)

```python
apply_operation(sandbox_root: Path, operation: PatchOperation,
                 allow_live_workspace: bool = False) -> ApplyResult
```

Flujo real:
1. Rechaza si `sandbox_root == WORKSPACE_ROOT` (salvo
   `allow_live_workspace=True`).
2. Rechaza si `operation.file` resuelve fuera de `sandbox_root`.
3. Para MODIFY/DELETE/REPLACE: verifica que el fingerprint REAL actual
   coincida con `old_fingerprint` -- si no, `FINGERPRINT_MISMATCH`, no
   escribe nada.
4. Aplica la operacion (reemplaza/borra/inserta lineas) y escribe.

## Las 4 operaciones

| Operacion | Requiere fingerprint | Comportamiento |
|---|---|---|
| `MODIFY` | Si | Reemplaza `[line_start, line_end]` con `new_content` |
| `REPLACE` | Si | Identico a MODIFY (alias semantico) |
| `DELETE` | Si | Elimina `[line_start, line_end]` |
| `ADD` | No | Inserta `new_content` en `line_start` (o al final si no se especifica) |

## Estados posibles (`ApplyResult.status`)

`APPLIED` / `FINGERPRINT_MISMATCH` / `FILE_NOT_FOUND` /
`REJECTED_OUTSIDE_SANDBOX` / `ERROR`.

## Verificado real (no solo con fixtures)

Sobre el sandbox real del caso Renting: las 4 operaciones aplican
correctamente sobre `renting/api/views.py` real; un fingerprint que no
coincide bloquea la escritura (archivo verificado intacto despues); un
symlink dentro del sandbox apuntando afuera se rechaza (probado con un
symlink real, no simulado).
