"""
Unit tests para ai_editor/repository/ -- POST-GRAPH 7 "Repository
Sandbox" (rediseno "AI Editor Runtime", 2026-08-11). Aislados: usan un
`ChangePlan` sintetico apuntando a archivos reales de ESTE MISMO repo
(`ai_editor/workspace.py`, siempre presente) para no depender de que el
Knowledge Graph este construido; la prueba de que el sandbox copia
archivos backend+frontend REALES desde el grafo completo (y que
`apply_operation()` sobre el sandbox nunca toca el checkout real) vive en
test_pipeline_equivalence.py.
"""
from ai_editor.repository import create_sandbox


def _plan_dict(steps):
    return {"context": {}, "steps": steps, "status": "PLANNED", "blocked_reason": None}


def _step(file):
    return {"step": 1, "file": file, "symbol": None, "line_start": None, "line_end": None,
            "operation": "MODIFY", "reason": "r", "dependencies": [], "risk": "LOW", "validation": "v"}


def test_create_sandbox_copies_a_real_file_into_an_isolated_temp_dir():
    from ai_editor.workspace import WORKSPACE_ROOT

    plan = _plan_dict([_step("ai_editor/workspace.py")])

    sandbox = create_sandbox(plan)
    try:
        assert sandbox.copied_files == ["ai_editor/workspace.py"]
        copied_path = sandbox.root / "ai_editor/workspace.py"
        real_path = WORKSPACE_ROOT / "ai_editor" / "workspace.py"
        assert copied_path.exists()
        assert copied_path.read_text(encoding="utf-8") == real_path.read_text(encoding="utf-8")
        assert sandbox.root != WORKSPACE_ROOT  # copia real, no un alias del checkout real
    finally:
        sandbox.cleanup()


def test_sandbox_cleanup_removes_the_temp_directory():
    plan = _plan_dict([_step("ai_editor/workspace.py")])
    sandbox = create_sandbox(plan)
    root = sandbox.root
    assert root.exists()

    sandbox.cleanup()

    assert not root.exists()


def test_sandbox_context_manager_cleans_up_automatically():
    plan = _plan_dict([_step("ai_editor/workspace.py")])

    with create_sandbox(plan) as sandbox:
        root = sandbox.root
        assert root.exists()

    assert not root.exists()


def test_sandbox_skips_sensitive_paths_without_copying_them():
    plan = _plan_dict([
        _step("ai_editor/workspace.py"),
        _step(".env"),
        _step("some/secrets/credentials.json"),
    ])

    sandbox = create_sandbox(plan)
    try:
        assert sandbox.copied_files == ["ai_editor/workspace.py"]
        assert set(sandbox.skipped_sensitive) == {".env", "some/secrets/credentials.json"}
        assert not (sandbox.root / ".env").exists()
    finally:
        sandbox.cleanup()


def test_sandbox_ignores_steps_without_a_file():
    plan = _plan_dict([_step(None)])

    sandbox = create_sandbox(plan)
    try:
        assert sandbox.copied_files == []
    finally:
        sandbox.cleanup()


def test_sandbox_deduplicates_repeated_files_across_steps():
    plan = _plan_dict([_step("ai_editor/workspace.py"), _step("ai_editor/workspace.py")])

    sandbox = create_sandbox(plan)
    try:
        assert sandbox.copied_files == ["ai_editor/workspace.py"]
    finally:
        sandbox.cleanup()


def test_sandbox_silently_skips_files_that_do_not_resolve_on_disk():
    """POST-GRAPH 5 (validate_plan) deberia haber bloqueado esto antes,
    pero el sandbox no debe crashear si de todos modos recibe un plan con
    un archivo que no existe -- lo omite, no lo copia."""
    plan = _plan_dict([_step("this/file/does/not/exist.py")])

    sandbox = create_sandbox(plan)
    try:
        assert sandbox.copied_files == []
    finally:
        sandbox.cleanup()
