"""
Unit tests para POST-GRAPH 18 "Hardening" (rediseno "AI Editor Runtime",
2026-08-11). Cubre las 3 mejoras reales de esta fase (patrones sensibles
extendidos, limite de archivos en el sandbox, limite de tamano de
contenido en un patch) mas la verificacion de symlinks (ya cubierta
desde POST-GRAPH 6/7, confirmada aca de nuevo explicitamente).
"""
import os

import pytest

from ai_editor.patch import MAX_PATCH_CONTENT_BYTES, OPERATION_ADD, OPERATION_MODIFY, PatchOperation, apply_operation
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.repository.sandbox import MAX_SANDBOX_FILES, create_sandbox


def _plan_dict(steps):
    return {"steps": steps}


def _step(file):
    return {"step": 1, "file": file, "symbol": None, "line_start": None, "line_end": None,
             "operation": "MODIFY", "reason": "r", "dependencies": [], "risk": "LOW", "validation": "v"}


@pytest.mark.parametrize("sensitive_path", [
    ".env", "path/to/secret.txt", "notes/credential_list.md", "server.pem",
    "id_rsa", "cert.crt", "ssl.cer", "db_backup.sql", "dump.sql.gz", "id_ed25519",
])
def test_sensitive_patterns_are_skipped_not_copied(sensitive_path):
    plan = _plan_dict([_step(sensitive_path)])
    sandbox = create_sandbox(plan)
    try:
        assert sandbox.copied_files == []
        assert sandbox.skipped_sensitive == [sensitive_path]
    finally:
        sandbox.cleanup()


def test_sandbox_caps_at_max_files_and_reports_the_overflow():
    steps = [_step(f"ai_editor/workspace.py") for _ in range(1)]  # 1 real file valido
    # Fuerza el limite bajo para no tener que fabricar 500 archivos reales.
    import ai_editor.repository.sandbox as sandbox_module
    original_limit = sandbox_module.MAX_SANDBOX_FILES
    sandbox_module.MAX_SANDBOX_FILES = 0
    try:
        plan = _plan_dict(steps)
        sandbox = create_sandbox(plan)
        try:
            assert sandbox.copied_files == []
            assert sandbox.files_over_limit == ["ai_editor/workspace.py"]
        finally:
            sandbox.cleanup()
    finally:
        sandbox_module.MAX_SANDBOX_FILES = original_limit


def test_patch_operation_rejects_content_over_the_size_limit():
    with pytest.raises(ValueError):
        PatchOperation(
            file="x.py", operation=OPERATION_ADD, line_start=1, line_end=1,
            old_fingerprint=None, new_content="x" * (MAX_PATCH_CONTENT_BYTES + 1), reason="test",
        )


def test_patch_operation_accepts_content_under_the_size_limit():
    op = PatchOperation(
        file="x.py", operation=OPERATION_ADD, line_start=1, line_end=1,
        old_fingerprint=None, new_content="x" * 1000, reason="test",
    )
    assert op.new_content is not None


def test_apply_operation_rejects_a_symlink_that_escapes_the_sandbox(tmp_path):
    """Verificacion explicita (no solo inferida) de que `.resolve()` en
    `apply_operation` sigue symlinks antes del chequeo de limites -- un
    symlink dentro del sandbox que apunta afuera se rechaza, nunca
    escribe en el destino real del symlink. Se intenta crear el symlink
    de verdad (no se asume por nombre de SO si el entorno lo permite) --
    se saltea solo si el intento real falla (ej. Windows sin privilegios)."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("SECRETO ORIGINAL\n", encoding="utf-8")

    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    try:
        os.symlink(outside / "secret.txt", sandbox_dir / "link.txt")
    except OSError as exc:
        pytest.skip(f"symlinks no soportados en este entorno: {exc}")

    fp = compute_fingerprint("SECRETO ORIGINAL\n")
    op = PatchOperation(file="link.txt", operation=OPERATION_MODIFY, line_start=1, line_end=1,
                         old_fingerprint=fp, new_content="HACKEADO\n", reason="test")

    result = apply_operation(sandbox_dir, op)

    assert result.status == "REJECTED_OUTSIDE_SANDBOX"
    assert (outside / "secret.txt").read_text(encoding="utf-8") == "SECRETO ORIGINAL\n"
