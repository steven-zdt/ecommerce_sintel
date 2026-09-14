"""
Unit tests para ai_editor/patch/ -- POST-GRAPH 6 "Patch Engine" (rediseno
"AI Editor Runtime", 2026-08-11). TODOS estos tests escriben UNICAMENTE
dentro de `tmp_path` (pytest fixture, un directorio temporal real por
test, borrado despues) -- por disciplina explicita de esta fase, NUNCA
contra `ai_editor.workspace.WORKSPACE_ROOT` ni ningun archivo real del
repo. El test que confirma el guardrail que rechaza `WORKSPACE_ROOT`
mismo es la unica prueba que referencia `WORKSPACE_ROOT`, y no escribe
nada (la operacion se rechaza antes de tocar el disco).
"""
import pytest

from ai_editor.patch import (
    STATUS_APPLIED,
    STATUS_FILE_NOT_FOUND,
    STATUS_FINGERPRINT_MISMATCH,
    STATUS_REJECTED_OUTSIDE_SANDBOX,
    OPERATION_ADD,
    OPERATION_DELETE,
    OPERATION_MODIFY,
    PatchOperation,
    apply_operation,
    build_operation_fingerprint,
    compute_fingerprint,
    read_lines_fingerprint,
)
from ai_editor.workspace import WORKSPACE_ROOT


@pytest.fixture()
def sample_file(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")
    return path


def test_compute_fingerprint_is_deterministic_and_content_sensitive():
    assert compute_fingerprint("hola") == compute_fingerprint("hola")
    assert compute_fingerprint("hola") != compute_fingerprint("chau")


def test_read_lines_fingerprint_matches_exact_real_content(sample_file):
    fp = read_lines_fingerprint(sample_file, 2, 3)
    assert fp == compute_fingerprint("line2\nline3\n")


def test_read_lines_fingerprint_returns_none_for_invalid_range(sample_file):
    assert read_lines_fingerprint(sample_file, 10, 20) is None
    assert read_lines_fingerprint(sample_file, 0, 1) is None


def test_apply_operation_rejects_the_real_workspace_root_by_default():
    """El guardrail estructural -- ni siquiera necesita un archivo real
    para rechazar, el chequeo ocurre ANTES de tocar disco."""
    operation = PatchOperation(
        file="does/not/matter.py", operation=OPERATION_MODIFY,
        line_start=1, line_end=1, old_fingerprint="x", new_content="y", reason="r",
    )

    result = apply_operation(WORKSPACE_ROOT, operation)

    assert result.status == STATUS_REJECTED_OUTSIDE_SANDBOX
    assert "WORKSPACE_ROOT" in result.detail


def test_apply_operation_modify_succeeds_when_fingerprint_matches(tmp_path, sample_file):
    expected_fp = compute_fingerprint("line2\nline3\n")
    operation = PatchOperation(
        file="sample.py", operation=OPERATION_MODIFY, line_start=2, line_end=3,
        old_fingerprint=expected_fp, new_content="REPLACED\n", reason="test",
    )

    result = apply_operation(tmp_path, operation)

    assert result.status == STATUS_APPLIED
    assert sample_file.read_text(encoding="utf-8") == "line1\nREPLACED\nline4\n"


def test_apply_operation_modify_stops_on_fingerprint_mismatch(tmp_path, sample_file):
    operation = PatchOperation(
        file="sample.py", operation=OPERATION_MODIFY, line_start=2, line_end=3,
        old_fingerprint="fingerprint-que-no-coincide", new_content="REPLACED\n", reason="test",
    )

    result = apply_operation(tmp_path, operation)

    assert result.status == STATUS_FINGERPRINT_MISMATCH
    # El archivo NO se toco -- la proteccion detuvo la escritura antes.
    assert sample_file.read_text(encoding="utf-8") == "line1\nline2\nline3\nline4\n"


def test_apply_operation_delete_removes_exact_lines(tmp_path, sample_file):
    fp = compute_fingerprint("line2\nline3\n")
    operation = PatchOperation(
        file="sample.py", operation=OPERATION_DELETE, line_start=2, line_end=3,
        old_fingerprint=fp, new_content=None, reason="test",
    )

    result = apply_operation(tmp_path, operation)

    assert result.status == STATUS_APPLIED
    assert sample_file.read_text(encoding="utf-8") == "line1\nline4\n"


def test_apply_operation_add_inserts_without_requiring_fingerprint(tmp_path, sample_file):
    operation = PatchOperation(
        file="sample.py", operation=OPERATION_ADD, line_start=2, line_end=2,
        old_fingerprint=None, new_content="INSERTED\n", reason="test",
    )

    result = apply_operation(tmp_path, operation)

    assert result.status == STATUS_APPLIED
    assert sample_file.read_text(encoding="utf-8") == "line1\nINSERTED\nline2\nline3\nline4\n"


def test_apply_operation_on_nonexistent_file_reports_file_not_found(tmp_path):
    operation = PatchOperation(
        file="ghost.py", operation=OPERATION_MODIFY, line_start=1, line_end=1,
        old_fingerprint="whatever", new_content="x", reason="test",
    )

    result = apply_operation(tmp_path, operation)

    assert result.status == STATUS_FILE_NOT_FOUND


def test_apply_operation_rejects_path_escaping_sandbox(tmp_path):
    operation = PatchOperation(
        file="../outside.py", operation=OPERATION_MODIFY, line_start=1, line_end=1,
        old_fingerprint="x", new_content="y", reason="test",
    )

    result = apply_operation(tmp_path, operation)

    assert result.status == STATUS_REJECTED_OUTSIDE_SANDBOX


def test_build_operation_fingerprint_reads_the_real_current_content(tmp_path, sample_file):
    operation = PatchOperation(
        file="sample.py", operation=OPERATION_MODIFY, line_start=1, line_end=1,
        old_fingerprint=None, new_content="x", reason="test",
    )

    fp = build_operation_fingerprint(tmp_path, operation)

    assert fp == compute_fingerprint("line1\n")


def test_invalid_operation_name_rejected_at_construction():
    with pytest.raises(ValueError):
        PatchOperation(
            file="x.py", operation="DESTROY_EVERYTHING", line_start=1, line_end=1,
            old_fingerprint=None, new_content=None, reason="test",
        )
