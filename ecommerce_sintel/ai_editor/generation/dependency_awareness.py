"""
`check_dependency_awareness()` -- FASE 40 "Dependency-Aware Generation"
(plan "AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "El LLM debe conocer las dependencias
relevantes. No permitir: nuevo import si genera circular dependency o
viola module boundary. Utilizar el Knowledge Graph para verificar."

**Alcance real, honesto**: el "conocer las dependencias" en tiempo de
GENERACION ya ocurre desde FASE 26 (`context.build_generation_context()`
incluye `graph_context.backend_dependencies`/`frontend_consumers`, ya
resueltos contra el grafo real). Esta fase es la VALIDACION posterior:
detecta que imports NUEVOS introduce una propuesta (diff `old_content`
vs `new_content`, no un parser AST completo) y los reporta para revision
humana.

**Lo que SI se bloquea, con una regla REAL y ya establecida (no
inventada)**: un import nuevo de `ai_engine` -- `ai_engine` es un
servicio FastAPI que corre en su PROPIO contenedor Docker (puerto 8100),
nunca un paquete Python importable desde el resto del proyecto (Regla 0
del rediseno del Knowledge Graph, verificada por test automatizado en
`project_knowledge_graph`: "ai_engine no conoce ni importa
project_knowledge_graph", y de forma simetrica, nada del resto del
proyecto deberia importar `ai_engine` como modulo Python).

**Lo que NO se implementa, honesto, no fabricado**: deteccion real de
dependencias CIRCULARES (requeriria recorrer el grafo de dependencias
completo para cada import nuevo, verificando si el modulo importado ya
depende -- transitivamente -- del archivo que se esta modificando; no
hay una operacion en `graph_sdk`/`graph_client` que exponga eso
directamente hoy, y fabricar una heuristica sin verificarla contra un
caso real seria exactamente lo que este proyecto evita en toda esta
sesion) ni verificacion exhaustiva de "module boundary" mas alla de la
regla `ai_engine` de arriba (el resto de boundaries del proyecto -- ej.
que app importa a cual -- no estan codificados como una lista
verificable en ningun documento real, inventar una lista seria fabricar
reglas).
"""
import re
from dataclasses import dataclass, field

SEVERITY_ERROR = "ERROR"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

_PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
_JS_IMPORT_RE = re.compile(
    r"""import\s+.*?from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)"""
)


@dataclass
class DependencyIssue:
    file: str
    module: str
    severity: str
    message: str

    def to_dict(self) -> dict:
        return {"file": self.file, "module": self.module, "severity": self.severity, "message": self.message}


@dataclass
class DependencyAwarenessReport:
    proposal_id: str
    status: str
    new_imports: dict = field(default_factory=dict)
    issues: list[DependencyIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "status": self.status,
            "new_imports": self.new_imports,
            "issues": [i.to_dict() for i in self.issues],
        }


def _extract_imports(content: str | None, suffix: str) -> set[str]:
    if not content:
        return set()
    if suffix == ".py":
        return {a or b for a, b in _PY_IMPORT_RE.findall(content)}
    if suffix in (".vue", ".js", ".ts"):
        return {a or b for a, b in _JS_IMPORT_RE.findall(content)}
    return set()


def check_dependency_awareness(proposal) -> DependencyAwarenessReport:
    """`proposal` es la `generation.models.PatchProposal` a evaluar."""
    issues: list[DependencyIssue] = []
    new_imports_by_file: dict[str, list[str]] = {}

    for op in proposal.operations:
        suffix = "." + op.file.rsplit(".", 1)[-1] if "." in op.file else ""
        old_imports = _extract_imports(op.old_content, suffix)
        new_imports = _extract_imports(op.new_content, suffix) - old_imports
        if not new_imports:
            continue
        new_imports_by_file[op.file] = sorted(new_imports)

        for module in new_imports:
            if module == "ai_engine" or module.startswith("ai_engine."):
                issues.append(DependencyIssue(
                    file=op.file, module=module, severity=SEVERITY_ERROR,
                    message=f"'{op.file}' introduce un import nuevo de '{module}' -- ai_engine "
                            "es un servicio FastAPI en su propio contenedor Docker, nunca un "
                            "paquete Python importable desde el resto del proyecto.",
                ))

    status = STATUS_FAIL if any(i.severity == SEVERITY_ERROR for i in issues) else STATUS_PASS
    return DependencyAwarenessReport(
        proposal_id=proposal.proposal_id, status=status,
        new_imports=new_imports_by_file, issues=issues,
    )


__all__ = [
    "check_dependency_awareness", "DependencyAwarenessReport", "DependencyIssue",
    "STATUS_PASS", "STATUS_FAIL",
]
