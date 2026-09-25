"""
ai_editor/change_store.py -- almacen EN MEMORIA de propuestas de cambio de codigo (plan MCP, FASE 7-8, 2026-09-25). SOLO DESARROLLO.

Una corrida de `run_autonomous_change_loop()` deja un sandbox VIVO (directorio temporal) que solo existe en el proceso que lo creo; por eso el
almacen es del proceso (dict + lock), con TTL y tope. Si el proceso se reinicia, las propuestas se pierden (se limpian los sandboxes al expirar).
No hay persistencia en BD a proposito: una propuesta perdida se vuelve a generar; nunca se promueve algo que no se pueda revalidar.

Este modulo NO decide aprobar nada: guarda el ApprovalRecord que una vista humana le entrega. La promocion usa `repository.promote_to_workspace()` con todas sus compuertas.
"""
import threading
import time
import uuid
from dataclasses import dataclass, field

TTL_SECONDS = 2 * 3600
MAX_ENTRIES = 20

_LOCK = threading.Lock()
_ENTRIES: dict = {}


@dataclass
class ChangeEntry:
    change_id: str
    owner_id: int
    request: str
    run: object                      # AgentRunResult (con sandbox vivo si APPROVAL_REQUIRED)
    created_at: float = field(default_factory=time.time)
    via_mcp: bool = False
    approval: object | None = None   # ApprovalRecord registrado por un humano
    approved_by: int | None = None
    promote_result: object | None = None
    rolled_back: bool = False

    @property
    def sandbox_result(self):
        return getattr(self.run, "sandbox_loop_result", None)

    def cleanup(self) -> None:
        loop = self.sandbox_result
        try:
            if loop is not None and getattr(loop, "sandbox", None) is not None:
                loop.sandbox.cleanup()
        except Exception:  # noqa: BLE001 - limpieza best-effort
            pass


def _evict_locked() -> None:
    now = time.time()
    for key in [k for k, e in _ENTRIES.items() if now - e.created_at > TTL_SECONDS]:
        _ENTRIES.pop(key).cleanup()
    while len(_ENTRIES) > MAX_ENTRIES:
        oldest = min(_ENTRIES, key=lambda k: _ENTRIES[k].created_at)
        _ENTRIES.pop(oldest).cleanup()


def put(owner_id: int, request_text: str, run, via_mcp: bool) -> ChangeEntry:
    entry = ChangeEntry(change_id="chg-" + uuid.uuid4().hex[:16], owner_id=owner_id, request=request_text, run=run, via_mcp=via_mcp)
    with _LOCK:
        _evict_locked()
        _ENTRIES[entry.change_id] = entry
    return entry


def get(change_id: str) -> ChangeEntry | None:
    with _LOCK:
        _evict_locked()
        return _ENTRIES.get(change_id)


def list_entries() -> list:
    with _LOCK:
        _evict_locked()
        return sorted(_ENTRIES.values(), key=lambda e: e.created_at, reverse=True)


def discard(change_id: str) -> bool:
    with _LOCK:
        entry = _ENTRIES.pop(change_id, None)
    if entry:
        entry.cleanup()
    return entry is not None


def state_of(entry: ChangeEntry) -> str:
    """Estado derivado: PROPOSED (sin decidir) | APPROVED | REJECTED | PROMOTED | ROLLED_BACK | FAILED (el loop no llego a revision)."""
    status = getattr(entry.run, "status", "")
    if entry.rolled_back:
        return "ROLLED_BACK"
    if entry.promote_result is not None and getattr(entry.promote_result, "status", "") == "PROMOTED":
        return "PROMOTED"
    if entry.approval is not None:
        return "APPROVED" if entry.approval.decision == "APPROVE" else "REJECTED"
    return "PROPOSED" if status == "APPROVAL_REQUIRED" else "FAILED"


def summarize(entry: ChangeEntry, full: bool = False) -> dict:
    run = entry.run
    loop = entry.sandbox_result
    gate = getattr(run, "promotion_gate_result", None)
    conf = getattr(run, "confidence_report", None)
    files = sorted(getattr(getattr(loop, "sandbox", None), "copied_files", []) or [])
    out = {
        "change_id": entry.change_id,
        "state": state_of(entry),
        "pipeline_status": getattr(run, "status", None),
        "detail": getattr(run, "detail", ""),
        "request": entry.request[:500],
        "files": files,
        "created_at": entry.created_at,
        "created_via_mcp": entry.via_mcp,
        "gate": gate.to_dict() if gate is not None and hasattr(gate, "to_dict") else None,
        "warnings": list(getattr(run, "warnings", []) or [])[:20],
        "ready_for_approval": bool(getattr(loop, "ready_for_approval", False)),
        "approval": entry.approval.to_dict() if entry.approval is not None else None,
        "promote": entry.promote_result.to_dict() if entry.promote_result is not None else None,
    }
    if conf is not None and hasattr(conf, "to_dict"):
        out["confidence"] = conf.to_dict()
    if full:
        out["required_tests"] = required_tests(run)
        out["human_review"] = (getattr(run, "human_review_text", "") or "")[:20000]
        out["reports"] = {}
        for name in ("code_quality_report", "architecture_report", "dependency_report", "contract_report",
                     "test_awareness_report", "documentation_report", "reconciliation_report", "impact_recheck_report"):
            rep = getattr(run, name, None)
            if rep is not None and hasattr(rep, "to_dict"):
                out["reports"][name] = rep.to_dict()
        vr = getattr(loop, "validation_report", None)
        if vr is not None and hasattr(vr, "to_dict"):
            out["validation_report"] = vr.to_dict()
    return out


def required_tests(run) -> dict:
    """Tests que HAY QUE correr (nunca los ejecuta este modulo ni el MCP)."""
    plan = getattr(run, "plan", None)
    proposal = getattr(getattr(run, "retry_outcome", None), "final_result", None)
    proposal = getattr(proposal, "proposal", None)
    return {
        "tests_to_update": list(getattr(proposal, "tests_to_update", []) or []),
        "tests_to_add": list(getattr(proposal, "tests_to_add", []) or []),
        "plan_tests": [str(t) for t in (getattr(plan, "tests", None) or [])][:50],
        "note": "El MCP no ejecuta suites de tests. Corrigelas manualmente antes de promover y de desplegar.",
    }
