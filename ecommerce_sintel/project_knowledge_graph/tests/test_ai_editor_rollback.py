"""
Unit tests para ai_editor/repository/rollback.py -- POST-GRAPH 16
"Rollback" (rediseno "AI Editor Runtime", 2026-08-11). Todos operan sobre
`tmp_path` -- nunca sobre `ai_editor.workspace.WORKSPACE_ROOT`.
"""
from ai_editor.approval.schema import ApprovalRecord, DECISION_APPROVE
from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.repository import (
    STATUS_NOTHING_TO_ROLLBACK,
    STATUS_ROLLED_BACK,
    Sandbox,
    promote_to_workspace,
    rollback_promotion,
)
from ai_editor.repository.promote import PromoteResult


def _promoted_result(fake_workspace, tmp_path):
    (fake_workspace).mkdir(parents=True, exist_ok=True)
    (fake_workspace / "app.py").write_text("ORIGINAL\n", encoding="utf-8")

    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    (sandbox_dir / "app.py").write_text("ORIGINAL\n", encoding="utf-8")
    fp = compute_fingerprint("ORIGINAL\n")
    sandbox = Sandbox(root=sandbox_dir, copied_files=["app.py"], original_fingerprints={"app.py": fp})

    op = PatchOperation(file="app.py", operation=OPERATION_ADD, line_start=1, line_end=1,
                         old_fingerprint=None, new_content="MODIFICADO\n", reason="test")
    apply_operation(sandbox.root, op)

    approved = ApprovalRecord(decision=DECISION_APPROVE)
    return promote_to_workspace(sandbox, approved, fake_workspace, confirm=True)


def test_promote_result_captures_original_content_before_overwriting(tmp_path):
    fake_workspace = tmp_path / "fake_workspace"
    result = _promoted_result(fake_workspace, tmp_path)

    assert result.status == "PROMOTED"
    assert result.files_before == {"app.py": "ORIGINAL\n"}


def test_rollback_restores_the_exact_original_content(tmp_path):
    fake_workspace = tmp_path / "fake_workspace"
    result = _promoted_result(fake_workspace, tmp_path)
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "MODIFICADO\nORIGINAL\n"

    rollback = rollback_promotion(fake_workspace, result)

    assert rollback.status == STATUS_ROLLED_BACK
    assert rollback.files_restored == ["app.py"]
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "ORIGINAL\n"


def test_rollback_on_a_non_promoted_result_does_nothing(tmp_path):
    fake_workspace = tmp_path / "fake_workspace"
    fake_workspace.mkdir()
    (fake_workspace / "app.py").write_text("INTACTO\n", encoding="utf-8")

    not_promoted = PromoteResult(status="NOT_APPROVED")
    rollback = rollback_promotion(fake_workspace, not_promoted)

    assert rollback.status == STATUS_NOTHING_TO_ROLLBACK
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "INTACTO\n"


def test_rollback_on_empty_files_before_does_nothing(tmp_path):
    fake_workspace = tmp_path / "fake_workspace"
    fake_workspace.mkdir()
    promoted_but_empty = PromoteResult(status="PROMOTED", files_before={})

    rollback = rollback_promotion(fake_workspace, promoted_but_empty)

    assert rollback.status == STATUS_NOTHING_TO_ROLLBACK


def test_to_dict_never_includes_full_file_content_only_a_count(tmp_path):
    fake_workspace = tmp_path / "fake_workspace"
    result = _promoted_result(fake_workspace, tmp_path)

    as_dict = result.to_dict()

    assert "files_before" not in as_dict
    assert as_dict["files_before_count"] == 1
