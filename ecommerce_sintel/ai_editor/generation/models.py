"""
Modelos de dominio de `ai_editor.generation` -- FASE 25 "Generation Domain
Model" (plan "AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro aplicada aca: "No utilizar strings libres como
unica representacion de un patch. Toda modificacion debe estar
estructurada." Estos dataclasses son el CONTRATO entre el LLM (via
`generator.py`) y el resto del pipeline (`validators.py` -> FASE 29 ->
Patch Engine real, FASE 31) -- ningun consumidor de una `PatchProposal`
debe tener que parsear texto libre.

`PatchOperation` de aca NO es `ai_editor.patch.schema.PatchOperation`
(POST-GRAPH 6) -- son dos capas distintas a proposito:
  - `generation.models.PatchOperation`: lo que el LLM PROPONE. Incluye
    `old_content` (texto exacto que el LLM cree que hay ahi -- permite
    verificar la propuesta contra el archivo real ANTES de tocar nada) y
    `old_hash`/`expected_hash` (declarados por el LLM, no confiables por
    si solos).
  - `patch.schema.PatchOperation`: lo que el Patch Engine REALMENTE
    aplica sobre un sandbox, con `old_fingerprint` calculado por
    `patch.fingerprint.compute_fingerprint()` sobre el archivo real (la
    unica fuente de verdad de hash de todo el sistema).
FASE 31 "Patch Engine Integration" es la que convierte una de una a la
otra, DESPUES de que `validators.py` (FASE 29) confirme que
`old_content` coincide con el archivo real -- nunca antes.
"""
from dataclasses import dataclass, field

from ai_editor.patch.schema import (
    OPERATION_ADD,
    OPERATION_DELETE,
    OPERATION_MODIFY,
    OPERATION_REPLACE,
)

# Mismo vocabulario de operaciones que el Patch Engine (POST-GRAPH 6) --
# una propuesta de generacion solo tiene sentido si eventualmente puede
# convertirse 1:1 en una operacion que el Patch Engine ya sabe aplicar.
GENERATION_OPERATIONS = {OPERATION_MODIFY, OPERATION_ADD, OPERATION_DELETE, OPERATION_REPLACE}

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

STATUS_PROPOSED = "PROPOSED"
STATUS_REJECTED = "REJECTED"
STATUS_ERROR = "ERROR"

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"


@dataclass
class GenerationConfidence:
    """Confianza AUTO-REPORTADA por el LLM (campo `confidence` de la salida
    estructurada, FASE 28) mas la clasificacion HIGH/MEDIUM/LOW derivada
    por umbral (FASE 44 "Confidence Engine" construira los factores
    reales -- graph certainty/contract certainty/etc; hasta entonces, el
    unico dato real disponible es lo que el LLM declara sobre su propia
    respuesta, nunca se fabrica un numero adicional)."""

    score: float
    level: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score fuera de rango [0, 1]: {self.score}")
        if self.level not in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW):
            raise ValueError(f"level invalido: '{self.level}'")

    @classmethod
    def from_score(cls, score: float) -> "GenerationConfidence":
        if score >= 0.8:
            level = CONFIDENCE_HIGH
        elif score >= 0.5:
            level = CONFIDENCE_MEDIUM
        else:
            level = CONFIDENCE_LOW
        return cls(score=score, level=level)

    def to_dict(self) -> dict:
        return {"score": self.score, "level": self.level}


@dataclass
class GenerationIssue:
    """Un problema encontrado validando la salida del LLM (FASE 29) --
    nunca se descarta en silencio, siempre queda registrado aca."""

    code: str
    message: str
    severity: str = SEVERITY_ERROR
    field: str | None = None

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "severity": self.severity, "field": self.field}


@dataclass
class PatchOperation:
    """Una operacion PROPUESTA por el LLM -- ver docstring del modulo
    para la distincion con `patch.schema.PatchOperation`."""

    file: str
    symbol: str | None
    operation: str
    old_content: str | None
    new_content: str | None
    old_hash: str | None
    expected_hash: str | None
    reason: str

    def __post_init__(self) -> None:
        if self.operation not in GENERATION_OPERATIONS:
            raise ValueError(f"operation invalida: '{self.operation}' -- validas: {GENERATION_OPERATIONS}")

    def to_dict(self) -> dict:
        return {
            "file": self.file, "symbol": self.symbol, "operation": self.operation,
            "old_content": self.old_content, "new_content": self.new_content,
            "old_hash": self.old_hash, "expected_hash": self.expected_hash,
            "reason": self.reason,
        }


@dataclass
class PatchProposal:
    """La propuesta completa del LLM para un `ChangeGenerationRequest` --
    NUNCA se promueve directo, siempre pasa por `validators.py` (FASE 29)
    y despues por el Patch Engine real (FASE 31)."""

    proposal_id: str
    change_id: str
    operations: list[PatchOperation]
    reasoning_summary: str
    confidence: GenerationConfidence
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    validation_requirements: list[str] = field(default_factory=list)
    tests_to_update: list[str] = field(default_factory=list)
    # FASE 42 "Test-Aware Generation": distincion explicita entre
    # "actualizar un test existente" (ya cubierto por tests_to_update
    # desde FASE 25) y "agregar uno nuevo"/"eliminar uno" -- el prompt
    # maestro pide las 3 categorias por separado, nunca fusionadas
    # ("no eliminar tests simplemente porque dificultan el cambio" solo
    # tiene sentido si "eliminar" es una categoria propia, declarada
    # explicitamente, no inferida).
    tests_to_add: list[str] = field(default_factory=list)
    tests_to_remove: list[str] = field(default_factory=list)
    # FASE 43 "Documentation-Aware Generation": identificar que
    # documentacion QUEDARIA desactualizada -- nunca se modifica
    # automaticamente (regla explicita del prompt maestro), solo se
    # declara para revision humana.
    documentation_to_update: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "change_id": self.change_id,
            "operations": [op.to_dict() for op in self.operations],
            "reasoning_summary": self.reasoning_summary,
            "confidence": self.confidence.to_dict(),
            "risks": self.risks, "assumptions": self.assumptions,
            "validation_requirements": self.validation_requirements,
            "tests_to_update": self.tests_to_update,
            "tests_to_add": self.tests_to_add, "tests_to_remove": self.tests_to_remove,
            "documentation_to_update": self.documentation_to_update,
        }


@dataclass
class ChangeGenerationRequest:
    """Lo que efectivamente se le entrega a `generator.py` -- ensamblado
    por `context.py` (FASE 26). Regla de contexto minimo (seccion 5 del
    prompt maestro): NUNCA el grafo completo, solo estos 6 campos ya
    comprimidos/filtrados."""

    change_intent: dict
    change_plan: dict
    graph_context: dict
    source_context: dict
    test_context: dict
    architecture_context: dict

    def to_dict(self) -> dict:
        return {
            "change_intent": self.change_intent, "change_plan": self.change_plan,
            "graph_context": self.graph_context, "source_context": self.source_context,
            "test_context": self.test_context, "architecture_context": self.architecture_context,
        }


@dataclass
class RetryAttempt:
    """Un intento individual dentro de un `RetryOutcome` -- FASE 30
    "Generation Retry Engine". `correction_note` es el texto exacto que
    se le paso al SIGUIENTE intento como `previous_attempts` (`None` en
    el ultimo intento, no hay uno "siguiente" que corregir)."""

    attempt: int
    status: str
    issues: list[GenerationIssue] = field(default_factory=list)
    correction_note: str | None = None

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt, "status": self.status,
            "issues": [i.to_dict() for i in self.issues],
            "correction_note": self.correction_note,
        }


@dataclass
class RetryOutcome:
    """Resultado completo de `retry.generate_with_retry()` -- conserva el
    HISTORIAL completo de intentos (regla del prompt maestro: "CADA RETRY
    DEBE EXPLICAR: error, causa, restriccion añadida, correccion
    solicitada"), no solo el ultimo resultado."""

    attempts: list[RetryAttempt]
    final_result: "GenerationResult"
    succeeded: bool

    def to_dict(self) -> dict:
        return {
            "attempts": [a.to_dict() for a in self.attempts],
            "final_result": self.final_result.to_dict(),
            "succeeded": self.succeeded,
        }


@dataclass
class GenerationResult:
    """Resultado de UN intento de generacion (FASE 30 "Retry Engine"
    encadenara varios de estos; por ahora, FASE 24-28, un unico intento
    sin reintento automatico)."""

    status: str
    proposal: PatchProposal | None
    issues: list[GenerationIssue] = field(default_factory=list)
    attempt: int = 1
    raw_llm_text: str | None = None
    # FASE 48 "Generation Audit": el prompt maestro pide registrar
    # "model, model version" -- gap real encontrado en la propia
    # verificacion de esa fase, `GenerationResult` nunca guardaba de
    # donde vino la respuesta. `provider`/`model` vienen tal cual de
    # `LLMResponse` (POST-GRAPH 2) -- nunca la API key, esa nunca llega
    # hasta aca.
    provider: str | None = None
    model: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "proposal": self.proposal.to_dict() if self.proposal else None,
            "issues": [i.to_dict() for i in self.issues],
            "attempt": self.attempt,
            "raw_llm_text": self.raw_llm_text,
            "provider": self.provider, "model": self.model,
        }


@dataclass
class PatchApplicationResult:
    """Resultado de `patch_integration.apply_proposal_to_sandbox()` --
    FASE 31 "Patch Engine Integration". `apply_results` son
    `ai_editor.patch.schema.ApplyResult` REALES (uno por operacion,
    devueltos por `patch.engine.apply_operation()`) -- este dataclass no
    los reimplementa, solo los agrupa junto con el resultado de la
    re-validacion previa (FASE 29) contra el repo."""

    proposal_id: str
    applied: bool
    apply_results: list = field(default_factory=list)
    pre_validation_issues: list[GenerationIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "applied": self.applied,
            "apply_results": [r.to_dict() for r in self.apply_results],
            "pre_validation_issues": [i.to_dict() for i in self.pre_validation_issues],
        }
