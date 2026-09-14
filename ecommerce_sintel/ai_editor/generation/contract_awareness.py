"""
`check_contract_coverage()` -- FASE 41 "Contract-Aware Generation" (plan
"AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "Si un cambio afecta un Endpoint, debe
verificar Serializer/Request/Response/Frontend Consumer/Tests. No
permitir que el LLM cambie SILENCIOSAMENTE un contrato utilizado por
multiples consumidores."

Construye sobre el `UNDECLARED_CONTRACT_CHANGE` de FASE 29 (degradado a
WARNING en FASE 38 -- un contrato REVIEW real ya no bloquea solo) --
esta fase agrega la parte de COBERTURA que el prompt maestro pide:
cuando el target afecta un contrato, comparar los consumidores
frontend/tests que el GRAFO ya conoce (`context.resolution`, real,
POST-GRAPH 3) contra lo que la `PatchProposal` realmente cubre
(`operations` tocadas + `tests_to_update` declarado). Si faltan
consumidores/tests conocidos, se REPORTA (nunca bloquea por si solo --
"no permitir que cambie SILENCIOSAMENTE" se cumple haciendolo VISIBLE en
el reporte, no prohibiendo el cambio; a veces un contrato cambia de
forma retrocompatible y genuinamente no necesita tocar cada consumidor).
"""
from dataclasses import dataclass, field

STATUS_FULL_COVERAGE = "FULL_COVERAGE"
STATUS_PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ContractCoverageReport:
    proposal_id: str
    status: str
    affects_contract: bool
    known_frontend_consumers: list[str] = field(default_factory=list)
    covered_frontend_consumers: list[str] = field(default_factory=list)
    missing_frontend_consumers: list[str] = field(default_factory=list)
    known_tests: list[str] = field(default_factory=list)
    covered_tests: list[str] = field(default_factory=list)
    missing_tests: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "status": self.status,
            "affects_contract": self.affects_contract,
            "frontend_consumers": {
                "known": self.known_frontend_consumers, "covered": self.covered_frontend_consumers,
                "missing": self.missing_frontend_consumers,
            },
            "tests": {
                "known": self.known_tests, "covered": self.covered_tests, "missing": self.missing_tests,
            },
            "recommendation": self.recommendation,
        }


def check_contract_coverage(proposal, context) -> ContractCoverageReport:
    """`proposal` es la `generation.models.PatchProposal`, `context` el
    `ChangeContext` (POST-GRAPH 3) original -- `resolution.contracts`
    (no vacio) es la senal REAL de que el target afecta un contrato,
    exactamente como ya lo calculo `calculate_change_impact()`."""
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    resolution = context_dict.get("resolution") or {}
    contracts = resolution.get("contracts") or []
    affects_contract = bool(contracts)

    if not affects_contract:
        return ContractCoverageReport(
            proposal_id=proposal.proposal_id, status=STATUS_NOT_APPLICABLE, affects_contract=False,
            recommendation="El target no afecta ningun contrato conocido -- no aplica cobertura.",
        )

    frontend_consumers = resolution.get("frontend_consumers") or []
    tests = resolution.get("tests") or {}
    known_tests_nodes = (tests.get("direct_tests") or []) + (tests.get("indirect_tests") or [])

    known_consumer_files = sorted({f["file"] for f in frontend_consumers if f.get("file")})
    known_test_names = sorted({t["name"] for t in known_tests_nodes if t.get("name")})

    touched_files = {op.file for op in proposal.operations}
    declared_tests = set(proposal.tests_to_update or [])

    covered_consumers = sorted(set(known_consumer_files) & touched_files)
    missing_consumers = sorted(set(known_consumer_files) - touched_files)
    covered_tests = sorted(set(known_test_names) & declared_tests)
    missing_tests = sorted(set(known_test_names) - declared_tests)

    if not missing_consumers and not missing_tests:
        status = STATUS_FULL_COVERAGE
        recommendation = "Todos los consumidores/tests conocidos por el grafo estan cubiertos por la propuesta."
    else:
        status = STATUS_PARTIAL_COVERAGE
        parts = []
        if missing_consumers:
            parts.append(f"{len(missing_consumers)} consumidor(es) frontend conocido(s) no tocado(s): {missing_consumers}")
        if missing_tests:
            parts.append(f"{len(missing_tests)} test(s) conocido(s) no declarado(s) en tests_to_update: {missing_tests}")
        recommendation = (
            "Este cambio afecta un contrato -- " + "; ".join(parts) +
            ". Revisar si es intencional (cambio retrocompatible) antes de aprobar."
        )

    return ContractCoverageReport(
        proposal_id=proposal.proposal_id, status=status, affects_contract=True,
        known_frontend_consumers=known_consumer_files, covered_frontend_consumers=covered_consumers,
        missing_frontend_consumers=missing_consumers,
        known_tests=known_test_names, covered_tests=covered_tests, missing_tests=missing_tests,
        recommendation=recommendation,
    )


__all__ = [
    "check_contract_coverage", "ContractCoverageReport",
    "STATUS_FULL_COVERAGE", "STATUS_PARTIAL_COVERAGE", "STATUS_NOT_APPLICABLE",
]
