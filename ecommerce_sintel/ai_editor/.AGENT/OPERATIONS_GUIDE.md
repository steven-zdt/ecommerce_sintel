# Guia de operacion de `ai_editor/`

Como usar el sistema en la practica -- ejemplos reales, no pseudocodigo.

## Configurar el LLM (POST-GRAPH 2)

```bash
# Ollama local (default, sin API key)
export AI_EDITOR_LLM_PROVIDER=ollama
export AI_EDITOR_OLLAMA_BASE_URL=http://localhost:11434
export AI_EDITOR_OLLAMA_MODEL=llama3.1:8b

# O OpenAI/Anthropic (requieren API key)
export AI_EDITOR_LLM_PROVIDER=anthropic
export AI_EDITOR_ANTHROPIC_API_KEY=sk-...
export AI_EDITOR_ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

O forzar un proveedor por-llamada sin tocar variables de entorno:
`interpret_request(request, provider="openai")`.

## Interpretar una solicitud

```python
from ai_editor.intent import interpret_request

intent = interpret_request("Permitir alquiler por horas en Renting")
if intent.status == "NEEDS_CLARIFICATION":
    print("Ambiguedades:", intent.ambiguities)
    # NO seguir -- pedir aclaracion real al usuario
```

## Resolver, planificar y validar (solo lectura, siempre seguro)

```python
from ai_editor.resolver import resolve_change_context
from ai_editor.planner import build_change_plan, validate_plan

context = resolve_change_context(intent)
plan = build_change_plan(context)
validation = validate_plan(plan)

if validation.status != "APPROVED":
    print("Bloqueado:", validation.issues)
```

## Inspeccionar el CHANGE SUMMARY antes de tocar nada

```python
from ai_editor.approval import build_change_summary

summary = build_change_summary(context, plan)
print(summary.render_text())
```

## Aplicar un cambio en sandbox (requiere `new_content` ya decidido)

```python
from ai_editor.repository import create_sandbox
from ai_editor.patch import apply_operation, PatchOperation, OPERATION_MODIFY
from ai_editor.patch.fingerprint import read_lines_fingerprint

with create_sandbox(plan) as sandbox:
    step = plan.steps[0]
    real_fp = read_lines_fingerprint(sandbox.root / step.file, step.line_start, step.line_end)

    operation = PatchOperation(
        file=step.file, operation=OPERATION_MODIFY,
        line_start=step.line_start, line_end=step.line_end,
        old_fingerprint=real_fp, new_content="...",  # decidido por un humano, no generado aca
        reason="...",
    )
    result = apply_operation(sandbox.root, operation)
```

## Validar sintaxis y revisar antes de aprobar

```python
from ai_editor.validation import run_validation, build_test_validation_report

validation_report = run_validation(sandbox, plan)
test_report = build_test_validation_report(context)
```

## Aprobar y promover -- REQUIERE decision humana real y `confirm=True`

```python
from ai_editor.approval import record_decision
from ai_editor.repository import promote_to_workspace

approval = record_decision("APPROVE", reviewer_note="revisado, se ve bien")

# workspace_root debe ser EXPLICITO -- nunca un default a WORKSPACE_ROOT real
result = promote_to_workspace(sandbox, approval, workspace_root, confirm=True)
```

**Esta guia NUNCA debe usarse para invocar `promote_to_workspace()`
contra el checkout real de este proyecto (`ai_editor.workspace.
WORKSPACE_ROOT`) sin que un humano lo confirme explicitamente en el
momento.**

## Revertir si algo sale mal

```python
from ai_editor.repository import rollback_promotion

rollback_promotion(workspace_root, result)  # solo si result.status == "PROMOTED"
```

## Auditar y consultar metricas

```python
from ai_editor.audit import audit_pipeline_run, compute_metrics

audit_pipeline_run(intent, context, plan, validation_report, test_report, approval, result)
print(compute_metrics())
```

## CLI

`ai_editor/` no tiene CLI propio todavia -- usar Python directo como en
los ejemplos de arriba. `project_knowledge_graph` si tiene CLI
(`python -m project_knowledge_graph.cli ...`), accesible indirectamente
via `graph_client`.
