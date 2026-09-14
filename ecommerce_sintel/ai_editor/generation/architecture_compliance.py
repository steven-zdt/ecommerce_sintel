"""
`check_architectural_compliance()` -- FASE 37 "Architectural Compliance"
(plan "AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro, aplicada literal: "No inventar reglas.
Utilizar documentacion arquitectonica existente como fuente."

Cada check de aca corresponde a una regla YA documentada y REAL de este
proyecto, citada explicitamente en el `source` de cada `ComplianceIssue`
-- nunca una "buena practica" generica inventada para esta fase:

  - Selectors sin efectos secundarios: `.AGENT.md` Service Layer --
    "Selectors: toda lectura en un Selector estatico. Sin efectos
    secundarios." (mismo texto que ya cita `ai_editor/planner/planner.py`).
  - ViewSets no tocan ORM directo: `.AGENT.md` -- "Los ViewSets no tocan
    ORM directamente -- solo llaman Commands y Selectors."
  - Import correcto de permisos: `CLAUDE.md` -- "Importacion correcta en
    ViewSets de negocio (nunca rest_framework.permissions.IsAdminUser):
    from users.api.permissions import IsAdminUser".
  - Frontend sin axios directo: `CLAUDE.md`/`MEMORY.md` -- "las
    peticiones se realizan a traves de useApi()... evitando llamar a
    axios directamente en los componentes."

**Lo que esta fase NO chequea, honesto, no oculto**: "tenant boundaries"
(el prompt maestro lo pide, pero este proyecto NO tiene un concepto de
tenant real ni documentado en ningun `.AGENT.md`/`CLAUDE.md` -- inventar
un chequeo sobre algo que no existe seria exactamente lo que la regla de
arriba prohibe) y "shared components" (requeriria parsear la estructura
real de componentes Vue -- props/slots/composicion --, fuera de alcance
de un chequeo por regex simple).

**Naturaleza de los checks**: heuristicos sobre `new_content` (regex/
substring), NO un parser AST completo de Python/Vue -- pueden tener
falsos negativos (un patron valido que la regex no reconozca) y, en
menor medida, falsos positivos (ej. un comentario que menciona
`.save()` sin ser una llamada real). Por eso los mas propensos a ruido
quedan como `WARNING` (revision humana), no `ERROR` bloqueante.
"""
import re
from dataclasses import dataclass, field

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

_SELECTOR_SIDE_EFFECT_RE = re.compile(r"\.(save|delete|create|update|bulk_create|bulk_update)\s*\(")
_ORM_CALL_RE = re.compile(r"\.objects\.")
_AXIOS_RE = re.compile(r"\baxios\.|from\s+['\"]axios['\"]|require\(\s*['\"]axios['\"]\s*\)")
_DRF_PERMISSIONS_IMPORT_RE = re.compile(r"from\s+rest_framework\.permissions\s+import\s+.*IsAdminUser")

_NOT_IMPLEMENTED_RULES = [
    "tenant boundaries -- este proyecto no tiene un concepto de tenant real/documentado en "
    "CLAUDE.md/.AGENT.md -- inventar un chequeo seria fabricar una regla que no existe.",
    "shared components -- requeriria parsear la estructura real de componentes Vue (props/"
    "slots/composicion), fuera de alcance de un chequeo por regex.",
]


@dataclass
class ComplianceIssue:
    rule: str
    file: str
    severity: str
    message: str
    source: str

    def to_dict(self) -> dict:
        return {
            "rule": self.rule, "file": self.file, "severity": self.severity,
            "message": self.message, "source": self.source,
        }


@dataclass
class ArchitecturalComplianceReport:
    proposal_id: str
    status: str
    issues: list[ComplianceIssue] = field(default_factory=list)
    not_implemented: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "status": self.status,
            "issues": [i.to_dict() for i in self.issues],
            "not_implemented": self.not_implemented,
        }


def _check_selector_side_effects(op) -> list[ComplianceIssue]:
    if "selectors.py" not in op.file.lower() or not op.new_content:
        return []
    matches = sorted(set(_SELECTOR_SIDE_EFFECT_RE.findall(op.new_content)))
    if not matches:
        return []
    return [ComplianceIssue(
        rule="selectors_no_side_effects", file=op.file, severity=SEVERITY_ERROR,
        message=f"'{op.file}' es un Selector -- se detecto {matches}, efecto(s) secundario(s) "
                "que un Selector no deberia tener.",
        source=".AGENT.md Service Layer: 'Selectors: toda lectura en un Selector estatico. "
               "Sin efectos secundarios.'",
    )]


def _check_viewset_orm_access(op) -> list[ComplianceIssue]:
    if "views.py" not in op.file.lower() or not op.new_content:
        return []
    if not _ORM_CALL_RE.search(op.new_content):
        return []
    return [ComplianceIssue(
        rule="viewsets_no_direct_orm", file=op.file, severity=SEVERITY_WARNING,
        message=f"'{op.file}' es un ViewSet -- se detecto '.objects.' (posible acceso ORM "
                "directo). Revisar que delegue a Commands/Selectors.",
        source=".AGENT.md: 'Los ViewSets no tocan ORM directamente -- solo llaman Commands y "
               "Selectors.'",
    )]


def _check_permissions_import(op) -> list[ComplianceIssue]:
    if "views.py" not in op.file.lower() or not op.new_content:
        return []
    if not _DRF_PERMISSIONS_IMPORT_RE.search(op.new_content):
        return []
    return [ComplianceIssue(
        rule="permissions_correct_import", file=op.file, severity=SEVERITY_ERROR,
        message=f"'{op.file}': import de IsAdminUser desde rest_framework.permissions -- debe "
                "ser 'from users.api.permissions import IsAdminUser'.",
        source="CLAUDE.md: 'Importacion correcta en ViewSets de negocio (nunca rest_framework."
               "permissions.IsAdminUser)'.",
    )]


def _check_frontend_axios(op) -> list[ComplianceIssue]:
    if not op.file.lower().endswith((".vue", ".js", ".ts")) or not op.new_content:
        return []
    if not _AXIOS_RE.search(op.new_content):
        return []
    return [ComplianceIssue(
        rule="frontend_no_direct_axios", file=op.file, severity=SEVERITY_ERROR,
        message=f"'{op.file}': uso de axios directo detectado -- debe usar useApi()/useAuth().",
        source="CLAUDE.md/.AGENT.md: 'las peticiones se realizan a traves de useApi()... "
               "evitando llamar a axios directamente en los componentes.'",
    )]


def check_architectural_compliance(proposal) -> ArchitecturalComplianceReport:
    """`proposal` es la `generation.models.PatchProposal` a evaluar."""
    issues: list[ComplianceIssue] = []
    for op in proposal.operations:
        issues.extend(_check_selector_side_effects(op))
        issues.extend(_check_viewset_orm_access(op))
        issues.extend(_check_permissions_import(op))
        issues.extend(_check_frontend_axios(op))

    status = STATUS_FAIL if any(i.severity == SEVERITY_ERROR for i in issues) else STATUS_PASS
    return ArchitecturalComplianceReport(
        proposal_id=proposal.proposal_id, status=status, issues=issues,
        not_implemented=list(_NOT_IMPLEMENTED_RULES),
    )


__all__ = [
    "check_architectural_compliance", "ArchitecturalComplianceReport", "ComplianceIssue",
    "STATUS_PASS", "STATUS_FAIL", "SEVERITY_ERROR", "SEVERITY_WARNING",
]
