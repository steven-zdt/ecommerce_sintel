"""
Unit tests para ai_editor/repository/promote.py -- POST-GRAPH 12 "Commit
Control" (rediseno "AI Editor Runtime", 2026-08-11). TODOS estos tests
operan sobre `tmp_path` (un directorio + repo git real pero TEMPORAL,
borrado al terminar el test) -- NUNCA sobre
`ai_editor.workspace.WORKSPACE_ROOT`. Ese es exactamente el punto de esta
fase: el mecanismo se prueba de verdad (incluye `git commit` real), pero
jamas contra el checkout real de este proyecto.
"""
import subprocess

import pytest

from ai_editor.approval.schema import ApprovalRecord, DECISION_APPROVE, DECISION_REJECT
from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.repository import (
    STATUS_NOT_APPROVED,
    STATUS_NOT_CONFIRMED,
    STATUS_PROMOTED,
    STATUS_WORKSPACE_DRIFT,
    Sandbox,
    commit_changes,
    promote_to_workspace,
)


@pytest.fixture()
def fake_workspace(tmp_path):
    root = tmp_path / "fake_workspace"
    root.mkdir()
    (root / "app.py").write_text("line1\nline2\n", encoding="utf-8")
    return root


@pytest.fixture()
def fake_git_workspace(fake_workspace):
    subprocess.run(["git", "init", "-q"], cwd=fake_workspace, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=fake_workspace, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=fake_workspace, check=True)
    subprocess.run(["git", "add", "."], cwd=fake_workspace, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=fake_workspace, check=True)
    return fake_workspace


def _sandbox_for(fake_workspace, tmp_path):
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    content = (fake_workspace / "app.py").read_text(encoding="utf-8")
    (sandbox_dir / "app.py").write_text(content, encoding="utf-8")
    return Sandbox(root=sandbox_dir, copied_files=["app.py"],
                    original_fingerprints={"app.py": compute_fingerprint(content)})


def test_promote_rejects_without_any_approval(fake_workspace, tmp_path):
    sandbox = _sandbox_for(fake_workspace, tmp_path)
    result = promote_to_workspace(sandbox, None, fake_workspace, confirm=True)
    assert result.status == STATUS_NOT_APPROVED
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_promote_rejects_a_rejected_approval_record(fake_workspace, tmp_path):
    sandbox = _sandbox_for(fake_workspace, tmp_path)
    rejected = ApprovalRecord(decision=DECISION_REJECT)
    result = promote_to_workspace(sandbox, rejected, fake_workspace, confirm=True)
    assert result.status == STATUS_NOT_APPROVED


def test_promote_rejects_approved_but_unconfirmed(fake_workspace, tmp_path):
    sandbox = _sandbox_for(fake_workspace, tmp_path)
    approved = ApprovalRecord(decision=DECISION_APPROVE)
    result = promote_to_workspace(sandbox, approved, fake_workspace, confirm=False)
    assert result.status == STATUS_NOT_CONFIRMED
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_promote_succeeds_when_approved_and_confirmed(fake_workspace, tmp_path):
    sandbox = _sandbox_for(fake_workspace, tmp_path)
    op = PatchOperation(file="app.py", operation=OPERATION_ADD, line_start=1, line_end=1,
                         old_fingerprint=None, new_content="INSERTED\n", reason="test")
    apply_operation(sandbox.root, op)
    approved = ApprovalRecord(decision=DECISION_APPROVE)

    result = promote_to_workspace(sandbox, approved, fake_workspace, confirm=True)

    assert result.status == STATUS_PROMOTED
    assert result.files_promoted == ["app.py"]
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "INSERTED\nline1\nline2\n"


def test_promote_blocks_all_or_nothing_when_workspace_drifted(fake_workspace, tmp_path):
    """Si el archivo real cambio desde que se creo el sandbox (edicion
    concurrente), la promocion se aborta COMPLETA -- ni ese archivo ni
    ningun otro se escribe."""
    sandbox = _sandbox_for(fake_workspace, tmp_path)
    (fake_workspace / "app.py").write_text("CAMBIO CONCURRENTE\n", encoding="utf-8")
    approved = ApprovalRecord(decision=DECISION_APPROVE)

    result = promote_to_workspace(sandbox, approved, fake_workspace, confirm=True)

    assert result.status == STATUS_WORKSPACE_DRIFT
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "CAMBIO CONCURRENTE\n"


def test_commit_changes_creates_a_real_local_commit_never_pushes(fake_git_workspace, tmp_path):
    (fake_git_workspace / "app.py").write_text("line1\nline2\nline3\n", encoding="utf-8")

    ok, detail = commit_changes(fake_git_workspace, ["app.py"], "feat: test commit")

    assert ok is True
    log = subprocess.run(["git", "log", "--oneline"], cwd=fake_git_workspace,
                          capture_output=True, text=True, check=True)
    assert "feat: test commit" in log.stdout
    # nunca hay un remoto configurado en este repo de prueba -- confirma
    # indirectamente que commit_changes() no intento (ni pudo) hacer push
    remotes = subprocess.run(["git", "remote"], cwd=fake_git_workspace,
                              capture_output=True, text=True, check=True)
    assert remotes.stdout.strip() == ""


def test_commit_changes_reports_failure_without_raising_on_non_git_directory(tmp_path):
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    (not_a_repo / "x.py").write_text("x = 1\n", encoding="utf-8")

    ok, detail = commit_changes(not_a_repo, ["x.py"], "message")

    assert ok is False
