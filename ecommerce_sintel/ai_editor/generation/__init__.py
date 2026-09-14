"""
`ai_editor.generation` -- AI CHANGE PROPOSAL ENGINE (plan "AI Change
Proposal Engine", 2026-08-11, FASE 24 en adelante).

Capa que transforma `ChangeIntent` + `ChangePlan` + contexto real del
grafo/codigo en una `PatchProposal` estructurada y verificable, y (desde
FASE 31) puede aplicarla sobre un SANDBOX aislado -- NUNCA sobre
`WORKSPACE_ROOT` directo. Promover al checkout real sigue siendo una
decision posterior, fuera del alcance de `generation/` (reusa
`repository.promote_to_workspace()` ya existente, POST-GRAPH 12, con
todos sus guardrails).

Submodulos (estado real al cierre de la primera ejecucion FASE 24-28,
ver `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md` para el detalle):
    models.py      -- FASE 25, dataclasses (ChangeGenerationRequest,
                       PatchProposal, PatchOperation, GenerationResult,
                       GenerationIssue, GenerationConfidence). REAL.
    context.py      -- FASE 26, `build_generation_context()`. REAL,
                       probado contra el repo real (renting/EquipmentViewSet).
    prompts.py       -- FASE 27, `build_prompt()` con 8 estrategias segun
                       tipo de cambio. REAL.
    generator.py    -- FASE 28, `generate_patch_proposal()`: LLM ->
                       JSON estructurado -> PatchProposal o REJECT. REAL,
                       pero sin probar todavia contra un LLM real (llm/
                       ya soporta Ollama/OpenAI/Anthropic, no se corrio
                       ninguno en esta fase -- ver checkpoint).
    validators.py    -- FASE 28, valida FORMA de la salida del LLM (tipos/
                       campos, nunca toca el repo real). REAL.
    proposal_validator.py -- FASE 29, `validate_proposal_against_repo()`:
                       valida una `PatchProposal` YA CONSTRUIDA CONTRA el
                       repo/plan reales (archivo existe, old_content/hash
                       coinciden, scope dentro del ChangePlan, sin tocar
                       contratos no declarados/archivos sensibles/limites).
                       Todavia NO conectado al Patch Engine (eso es FASE
                       31). REAL.
    retry.py         -- FASE 30, `generate_with_retry()`: orquesta
                       generator + proposal_validator con hasta
                       `DEFAULT_MAX_RETRIES=3` intentos, cada uno
                       reenviando al LLM una nota de correccion EXPLICITA
                       de por que fallo el intento anterior
                       (`RetryOutcome.attempts`, historial completo, nunca
                       solo el ultimo intento). REAL.
    patch_integration.py -- FASE 31, `apply_proposal_to_sandbox()`:
                       convierte una `PatchProposal` en operaciones REALES
                       del Patch Engine (`patch.schema.PatchOperation`,
                       con `old_fingerprint` calculado fresco) y las
                       aplica sobre un `Sandbox` YA CREADO por el caller
                       -- re-valida contra el repo real ANTES (FASE 29,
                       de nuevo, sin confiar en que el caller ya lo hizo)
                       y cada operacion vuelve a verificar su propio
                       fingerprint al aplicar (POST-GRAPH 6). Jamas llama
                       a `promote_to_workspace()` -- se detiene en
                       Sandbox, tal como pide el prompt maestro. REAL.
    sandbox_loop.py  -- FASE 32, `run_sandbox_validation_loop()`: ciclo
                       completo "probar esta propuesta de punta a punta"
                       en una sola llamada -- create_sandbox() + FASE 31
                       + `validation.run_validation()` (sintaxis, POST-
                       GRAPH 8) + `validation.build_test_validation_
                       report()` (POST-GRAPH 10, clasifica sin ejecutar).
                       `WORKSPACE_ROOT` nunca se toca. `ready_for_
                       approval` NO implica aprobacion humana ni tests
                       reales pasando -- solo "aplico + sintaxis OK". REAL.
    promotion.py     -- `review_and_promote()`: encadena SandboxLoopResult
                       (FASE 32) con `approval.build_change_summary()`/
                       `record_decision()` (POST-GRAPH 11) y `repository.
                       promote_to_workspace()` (POST-GRAPH 12) en un solo
                       flujo. `decision`/`confirm` DEBEN venir de un
                       humano real -- nunca defaulteados a un valor que
                       permita promover solo. Probado UNICAMENTE contra
                       `fake_workspace` (`tmp_path`), nunca contra
                       `WORKSPACE_ROOT` real (mismo criterio que
                       POST-GRAPH 12). REAL.
    validation_report.py -- FASE 33, `build_generation_validation_
                       report()`: consolida syntax/tests/contracts/
                       errors/warnings de un `SandboxLoopResult` (FASE
                       32) en un unico `GenerationValidationReport`. Cero
                       logica nueva -- agregacion honesta. `tests_
                       executed` queda `False` siempre: ejecutar tests
                       reales sigue `NOT_IMPLEMENTED`, mismo motivo
                       estructural de siempre (sandbox parcial, sin
                       Django/Postgres/Redis). REAL.
    reconciliation.py -- FASE 34, `reconcile_change_scope()`: compara el
                       SCOPE PREDICHO (plan/resolution, antes del patch)
                       contra el scope REAL de la `PatchProposal`
                       (archivos/simbolos declarados) -- formato PASS/
                       FAIL con conteos, tal como pide el ejemplo del
                       prompt maestro. Reconstruir el GRAFO COMPLETO
                       (GRAPH BEFORE/AFTER via re-scanning) sigue
                       `NOT_IMPLEMENTED`, mismo motivo estructural de
                       POST-GRAPH 9 (sandbox parcial). REAL.
    impact_recheck.py -- FASE 35, `capture_impact_baseline()` +
                       `recheck_impact()`: re-consulta `calculate_
                       impact()` sobre el mismo target y compara contra
                       un baseline capturado al planear -- detecta DRIFT
                       DEL GRAFO (alguien corrio `cli audit` mientras
                       tanto), no "impacto real de mi cambio" (eso
                       requeriria reconstruir el grafo, sigue sin ser
                       posible). Bug real encontrado y corregido durante
                       esta fase: una primera version aproximaba el
                       "predicho" sumando 3 buckets de `resolution`, que
                       excluyen tests/docs/config y producia falsos
                       BLOCK siempre -- corregido capturando el baseline
                       con una llamada real a `calculate_impact()`. REAL.
    code_quality.py  -- FASE 36, `run_code_quality_checks()`: detecta
                       que herramientas de lint/quality estan REALMENTE
                       configuradas+instaladas (auditoria real: solo
                       `bandit`, via `[tool.bandit]` en `pyproject.toml`
                       + bandit 1.9.4 instalado) y las corre de verdad
                       contra los archivos `.py` que la propuesta toco
                       dentro del sandbox, misma config que CI. JS/Vue:
                       `NOT_CONFIGURED` explicito (sin eslint/prettier
                       instalados), nunca fabricado. REAL.
    architecture_compliance.py -- FASE 37, `check_architectural_
                       compliance()`: valida `new_content` de una
                       propuesta contra reglas YA documentadas y reales
                       (CLAUDE.md/.AGENT.md, citadas en cada
                       `ComplianceIssue.source`) -- Selectors sin efectos
                       secundarios, ViewSets sin ORM directo, import
                       correcto de permisos, frontend sin axios directo.
                       Heuristico (regex sobre `new_content`), no un
                       parser AST completo. "tenant boundaries"/"shared
                       components" (que pide el prompt maestro) quedan
                       documentados como NO aplicables/NOT_IMPLEMENTED
                       -- este proyecto no tiene concepto de tenant real,
                       y "shared components" requeriria parsear Vue real.
                       REAL.
    dependency_awareness.py -- FASE 40, `check_dependency_awareness()`:
                       detecta imports NUEVOS de una propuesta (diff
                       old_content vs new_content) y bloquea ERROR si
                       alguno referencia `ai_engine` (regla real ya
                       establecida: servicio FastAPI en su propio
                       contenedor Docker, nunca un paquete Python
                       importable). Deteccion de dependencias circulares
                       NO implementada -- no hay una operacion real en
                       graph_sdk que la exponga, no se fabrica. REAL.
    contract_awareness.py -- FASE 41, `check_contract_coverage()`:
                       cuando el target afecta un contrato
                       (`resolution.contracts` no vacio), compara
                       consumidores frontend/tests YA conocidos por el
                       grafo contra lo que la propuesta realmente cubre
                       -- reporta cobertura completa/parcial, nunca
                       bloquea por si solo (un contrato puede cambiar de
                       forma retrocompatible sin tocar cada consumidor).
                       REAL.
    test_awareness.py -- FASE 42, `check_test_awareness()`:
                       `PatchProposal` distingue `tests_to_update`/
                       `tests_to_add`/`tests_to_remove` (FASE 25
                       extendido) -- ERROR si una operacion `DELETE`
                       toca un archivo de test SIN declararlo en
                       `tests_to_remove` ("no eliminar tests porque
                       dificultan el cambio"); declarado, queda como
                       WARNING visible. REAL.
    documentation_awareness.py -- FASE 43, `check_documentation_
                       awareness()`: `PatchProposal.documentation_to_
                       update` (campo nuevo) se compara contra la
                       documentacion que el grafo ya sabe que referencia
                       el target -- informativo, nunca bloquea (la doc
                       nunca se modifica automaticamente, ya garantizado
                       por FASE 38; esta funcion ademas re-verifica esa
                       garantia por defensa en profundidad). REAL.
    confidence_engine.py -- FASE 44, `compute_composite_confidence()`:
                       combina `PatchProposal.confidence` (auto-
                       reportada por el LLM) con `target_certainty`/
                       `syntax_validation`/`architecture_compliance`/
                       `contract_coverage` -- TODOS datos YA reales de
                       fases anteriores, cada factor OPCIONAL (si no se
                       corrio esa fase, no participa, nunca se fabrica).
                       Promedio simple, nunca una ponderacion inventada.
                       REAL.
    human_review.py  -- FASE 45, `render_full_review()`: texto humano
                       que compone TODOS los reportes de FASE 33-44
                       (patch/risks/confidence/graph diff/impact/
                       syntax/architecture/contratos/dependencias/tests/
                       documentacion) en un unico bloque -- sin UI real,
                       solo el render (mismo criterio que `approval.
                       gate.ChangeSummary.render_text()`, POST-GRAPH 11).
                       Cada reporte es opcional. REAL.
    promotion_gate.py -- FASE 46, `check_promotion_gate()`: consolida
                       Graph Reconciliation (FASE 34)/Impact Recheck
                       (FASE 35)/Architectural Compliance (FASE 37)/
                       Contract Coverage (FASE 41) como gates BLOQUEANTES
                       ANTES de someter la propuesta a revision humana.
                       "Tests pass" queda honestamente marcado como NO
                       VERIFICABLE (los tests nunca se ejecutan). NO
                       reemplaza `promotion.review_and_promote()` --
                       `decision`/`confirm` siguen siendo obligatorios
                       ahi, este gate es un chequeo PREVIO mas amplio.
                       REAL.
    promotion.py (FASE 47 "Rollback") -- `rollback_outcome()`: reusa
                       `repository.rollback.rollback_promotion()`
                       (POST-GRAPH 16) tal cual, aceptando el
                       `PromotionOutcome` de `review_and_promote()`
                       directo. Probado UNICAMENTE contra `fake_
                       workspace`, mismo criterio que `review_and_
                       promote()`. REAL.
    performance.py    -- FASE 56 "Performance",
                       `measure_pipeline_stage_timings()`: cronometra
                       (con `time.perf_counter()` real) cada etapa del
                       pipeline que NO depende de un LLM externo
                       (sandbox loop, code quality, reconciliation,
                       impact recheck, confidence, human review) contra
                       datos reales del repo. La etapa GENERATING (LLM)
                       queda siempre `NOT_MEASURED` -- ningun LLM real se
                       invoco durante todo el desarrollo de este plan,
                       nunca se fabrica un tiempo para ella. REAL.
    pipeline_states.py -- FASE 50 "Failure Recovery",
                       `classify_pipeline_state()`: clasifica el estado
                       ACTUAL de un cambio (los 15 estados nombrados por
                       el prompt maestro: RECEIVED..ROLLED_BACK) a partir
                       de los objetos YA reales de cada etapa -- funcion
                       de clasificacion honesta, no una maquina de
                       estados nueva que orqueste el pipeline (eso seria
                       FASE 53 "Autonomous Controlled Loop", fuera de
                       alcance). REAL.

Uso simple (un solo intento, sin retry):
    from ai_editor.generation import build_generation_context, generate_patch_proposal
    request = build_generation_context(intent, context, plan)
    result = generate_patch_proposal(request)
    if result.status == "PROPOSED":
        result.proposal  # PatchProposal, todavia SIN aplicar

Uso con retry + validacion contra el repo real (FASE 29+30):
    from ai_editor.generation import build_generation_context, generate_with_retry
    request = build_generation_context(intent, context, plan)
    outcome = generate_with_retry(request, plan, context)
    if outcome.succeeded:
        outcome.final_result.proposal  # PatchProposal validada, SIN aplicar
    else:
        outcome.attempts  # historial completo, cada uno con su correction_note
"""
from ai_editor.generation.architecture_compliance import (
    ArchitecturalComplianceReport,
    check_architectural_compliance,
)
from ai_editor.generation.code_quality import CodeQualityReport, run_code_quality_checks
from ai_editor.generation.confidence_engine import CompositeConfidenceReport, compute_composite_confidence
from ai_editor.generation.context import build_generation_context
from ai_editor.generation.contract_awareness import ContractCoverageReport, check_contract_coverage
from ai_editor.generation.dependency_awareness import (
    DependencyAwarenessReport,
    check_dependency_awareness,
)
from ai_editor.generation.documentation_awareness import (
    DocumentationAwarenessReport,
    check_documentation_awareness,
)
from ai_editor.generation.generator import generate_patch_proposal
from ai_editor.generation.impact_recheck import ImpactBaseline, capture_impact_baseline, recheck_impact
from ai_editor.generation.models import (
    ChangeGenerationRequest,
    GenerationConfidence,
    GenerationIssue,
    GenerationResult,
    PatchApplicationResult,
    PatchOperation,
    PatchProposal,
    RetryAttempt,
    RetryOutcome,
)
from ai_editor.generation.human_review import render_full_review
from ai_editor.generation.patch_integration import apply_proposal_to_sandbox
from ai_editor.generation.performance import PipelineTimingReport, measure_pipeline_stage_timings
from ai_editor.generation.pipeline_states import ALL_STATES, PipelineStatus, classify_pipeline_state
from ai_editor.generation.promotion import PromotionOutcome, review_and_promote, rollback_outcome
from ai_editor.generation.promotion_gate import PromotionGateResult, check_promotion_gate
from ai_editor.generation.proposal_validator import validate_proposal_against_repo
from ai_editor.generation.reconciliation import GraphReconciliationReport, reconcile_change_scope
from ai_editor.generation.retry import DEFAULT_MAX_RETRIES, generate_with_retry
from ai_editor.generation.sandbox_loop import SandboxLoopResult, run_sandbox_validation_loop
from ai_editor.generation.test_awareness import TestAwarenessReport, check_test_awareness
from ai_editor.generation.validation_report import (
    GenerationValidationReport,
    build_generation_validation_report,
)

__all__ = [
    "build_generation_context",
    "generate_patch_proposal",
    "validate_proposal_against_repo",
    "generate_with_retry",
    "apply_proposal_to_sandbox",
    "run_sandbox_validation_loop",
    "review_and_promote",
    "build_generation_validation_report",
    "reconcile_change_scope",
    "capture_impact_baseline",
    "recheck_impact",
    "run_code_quality_checks",
    "check_architectural_compliance",
    "check_dependency_awareness",
    "check_contract_coverage",
    "check_test_awareness",
    "check_documentation_awareness",
    "compute_composite_confidence",
    "render_full_review",
    "check_promotion_gate",
    "rollback_outcome",
    "classify_pipeline_state",
    "PipelineStatus",
    "ALL_STATES",
    "measure_pipeline_stage_timings",
    "PipelineTimingReport",
    "DEFAULT_MAX_RETRIES",
    "ChangeGenerationRequest",
    "PatchProposal",
    "PatchOperation",
    "GenerationResult",
    "GenerationIssue",
    "GenerationConfidence",
    "RetryAttempt",
    "RetryOutcome",
    "PatchApplicationResult",
    "SandboxLoopResult",
    "PromotionOutcome",
    "GenerationValidationReport",
    "GraphReconciliationReport",
    "ImpactBaseline",
    "CodeQualityReport",
    "ArchitecturalComplianceReport",
    "DependencyAwarenessReport",
    "ContractCoverageReport",
    "TestAwarenessReport",
    "DocumentationAwarenessReport",
    "CompositeConfidenceReport",
    "PromotionGateResult",
]
