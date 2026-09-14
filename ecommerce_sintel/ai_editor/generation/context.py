"""
`build_generation_context()` -- FASE 26 "Source Context Builder" (plan
"AI Change Proposal Engine", 2026-08-11).

Convierte `ChangePlan` + `ChangeContext.context_packet` (ya construido
por `graph_client.build_context_packet()`, Fase 12 del Site Knowledge
Graph -- ver POST-GRAPH 3) en el `ChangeGenerationRequest` completo que
`generator.py` (FASE 28) le pasa al LLM.

Regla del prompt maestro aplicada aca (seccion 5, "REGLA ABSOLUTA DE
CONTEXTO"): "No leer automaticamente todo el archivo si solamente se
necesita un simbolo." -- `_read_symbol_source()` solo lee el rango de
lineas real del step MAS un margen chico (no el archivo entero), y solo
para los steps `operation="MODIFY"` (lo unico que el LLM realmente
necesita ver para proponer `old_content`/`new_content` verbatim). Los
demas nodos relevantes (`contracts`/`frontend_consumers`/
`backend_dependencies`/`tests`/`documentation`) ya llegan COMPACTADOS
(id/type/name/file/lineas, sin fuente) en `graph_context` -- el LLM sabe
que existen y donde estan, no necesita leer su contenido completo para
saber que revisarlos.
"""
import re

from ai_editor.validation.tests import build_test_validation_report
from ai_editor.workspace import WORKSPACE_ROOT, resolve_repo_file
from ai_editor.generation.models import ChangeGenerationRequest

# Margen alrededor del rango exacto del step -- suficiente para ver
# firma/decoradores/imports cercanos de un metodo sin leer el archivo
# completo (ver ejemplo de la seccion "FASE 26" del prompt maestro:
# "AvailabilityService lineas 142-189 + imports relevantes + metodos
# dependientes + tests asociados" -- los "metodos dependientes"/"tests
# asociados" ya vienen resueltos por separado en `graph_context`/
# `test_context`, este margen solo cubre el entorno INMEDIATO del rango).
MARGIN_BEFORE = 10
MARGIN_AFTER = 5

# Heuristica documentada, no perfecta: en Python/JS/Vue los imports viven
# al principio del archivo -- tomar las primeras N lineas como "posibles
# imports" es barato y suficientemente preciso para este proyecto (no hay
# imports tardios/condicionales en el codigo real auditado). Si el rango
# pedido ya empieza dentro de esas N lineas, no se duplica.
IMPORT_HEADER_LINES = 40

_MEMORY_MD_GLOBAL_RULES_RE = re.compile(
    r"## 2\. Alineaci[oó]n con Reglas Generales.*?\n(.*?)\n## 3\.", re.DOTALL
)
_MEMORY_MD_RULE_LINE_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)


def _read_symbol_source(file_rel: str, line_start: int | None, line_end: int | None) -> dict | None:
    """Devuelve `None` si el archivo no resuelve contra el disco real
    (mismo criterio que `planner.validator` -- nunca se inventa contenido
    para un archivo que no existe)."""
    real_path = resolve_repo_file(file_rel)
    if real_path is None:
        return None

    lines = real_path.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)

    if line_start is None or line_end is None:
        # Nodo sin rango de lineas (ej. App/Endpoint sin Symbol asociado) --
        # no hay "el simbolo" que leer, no se lee el archivo completo igual.
        return {
            "file": file_rel, "requested_lines": None, "context_lines": None,
            "source": None, "imports_header": None,
            "note": "Este step no tiene rango de lineas (no es un Symbol) -- sin fuente que adjuntar.",
        }

    ctx_start = max(1, line_start - MARGIN_BEFORE)
    ctx_end = min(total, line_end + MARGIN_AFTER)
    snippet = "\n".join(lines[ctx_start - 1:ctx_end])

    header = None
    if ctx_start > IMPORT_HEADER_LINES + 1:
        header = "\n".join(lines[:IMPORT_HEADER_LINES])

    return {
        "file": file_rel,
        "requested_lines": f"{line_start}-{line_end}",
        "context_lines": f"{ctx_start}-{ctx_end}",
        "source": snippet,
        "imports_header": header,
    }


def build_source_context(plan) -> dict:
    """Lee fuente real para el target principal (`MODIFY`) y, desde
    FASE 38 "Cross-Stack Generation" (2026-08-11, relajado con
    confirmacion explicita del usuario), tambien para los steps `REVIEW`
    no-documentacion y `RUN` -- exactamente los mismos que `proposal_
    validator._check_scope_and_operation()` ahora acepta como
    escribibles. Sin esto, el LLM podria PROPONER un cambio cross-stack
    (permitido estructuralmente) pero nunca conocer el `old_content`
    real de esos archivos -- cualquier propuesta cross-stack fallaria
    `OLD_CONTENT_MISMATCH` (FASE 29) por adivinar contenido a ciegas.
    Documentacion (`.md`) sigue sin leerse aca -- FASE 43 la mantiene
    fuera del alcance de escritura automatica, no hace falta su fuente."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    targets = {}
    for step in plan_dict.get("steps") or []:
        file = step.get("file")
        if not file:
            continue
        is_documentation = file.lower().endswith(".md")
        writable = step["operation"] == "MODIFY" or (
            step["operation"] in ("REVIEW", "RUN") and not is_documentation
        )
        if not writable:
            continue
        source = _read_symbol_source(file, step.get("line_start"), step.get("line_end"))
        if source is not None:
            targets[step["step"]] = {**source, "symbol": step.get("symbol"), "reason": step.get("reason")}
    return {"targets": targets}


def _extract_global_rules() -> list[str]:
    """Lee las 5 reglas globales reales desde `MEMORY.md` (seccion
    "Alineacion con Reglas Generales") en vez de copiarlas a mano aca --
    si `MEMORY.md` cambia, este contexto se actualiza solo, sin arriesgar
    una copia hardcodeada desactualizada (regla del prompt maestro: "no
    inventar reglas, usar documentacion arquitectonica existente como
    fuente" -- FASE 37 la aplicara con mas profundidad, esto es la
    version minima necesaria para FASE 24-28)."""
    memory_path = WORKSPACE_ROOT / "MEMORY.md"
    if not memory_path.exists():
        return []
    text = memory_path.read_text(encoding="utf-8", errors="replace")
    section = _MEMORY_MD_GLOBAL_RULES_RE.search(text)
    if not section:
        return []
    return [line.strip() for line in _MEMORY_MD_RULE_LINE_RE.findall(section.group(1))]


def build_architecture_context(context) -> dict:
    """`app`/doc de arquitectura del target principal -- resuelto via
    `CLAUDE.md` (tabla de ruteo real), no una convencion de nombre
    adivinada (los nombres de archivo NO son uniformes entre apps, ej.
    `ARQUITECTURACOMPLETA_SETTING.md` vs `ARQUITECTURA_COMPLETA_RENTIG.md`
    -- confirmado leyendo CLAUDE.md real)."""
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    primary = context_dict.get("primary_target") or {}
    app = primary.get("app") or None

    doc_excerpt = None
    doc_path = None
    if app:
        claude_md = WORKSPACE_ROOT / "CLAUDE.md"
        if claude_md.exists():
            text = claude_md.read_text(encoding="utf-8", errors="replace")
            # [FASE 61.8, GAP G] algunas filas de CLAUDE.md llevan una anotacion
            # entre la celda de la app y la celda del doc (ej. "*(nueva, en
            # construccion)*" para organization/seo) -- `[^|]*` la tolera sin
            # cruzar a la fila siguiente (nunca matchea a traves de un `|` real).
            m = re.search(rf"\|\s*`ecommerce_sintel/{re.escape(app)}/`[^|]*\|\s*`([^`]+)`\s*\|", text)
            if m:
                rel_to_ecommerce = m.group(1)
                if rel_to_ecommerce.startswith("ecommerce_sintel/"):
                    rel_to_ecommerce = rel_to_ecommerce[len("ecommerce_sintel/"):]
                real_doc = resolve_repo_file(rel_to_ecommerce)
                if real_doc is not None:
                    doc_path = rel_to_ecommerce
                    doc_excerpt = real_doc.read_text(encoding="utf-8", errors="replace")[:2000]

    return {
        "app": app,
        "architecture_doc_path": doc_path,
        "architecture_doc_excerpt": doc_excerpt,
        "global_rules": _extract_global_rules(),
        "global_rules_source": "MEMORY.md seccion 'Alineacion con Reglas Generales' (leido en vivo, no copiado a mano).",
    }


def build_generation_context(intent, context, plan) -> ChangeGenerationRequest:
    """Punto de entrada de FASE 26 -- ensambla los 6 campos de
    `ChangeGenerationRequest` (FASE 25). `intent`/`context`/`plan` son los
    mismos objetos que ya produce el pipeline existente (POST-GRAPH 2/3/4),
    cero llamadas nuevas al grafo."""
    intent_dict = intent.to_dict() if hasattr(intent, "to_dict") else dict(intent)
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)

    return ChangeGenerationRequest(
        change_intent=intent_dict,
        change_plan=plan_dict,
        graph_context=context_dict.get("context_packet") or {},
        source_context=build_source_context(plan),
        test_context=build_test_validation_report(context),
        architecture_context=build_architecture_context(context),
    )
