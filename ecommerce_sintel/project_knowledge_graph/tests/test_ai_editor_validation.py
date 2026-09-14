"""
Unit tests para ai_editor/validation/ -- POST-GRAPH 8 "Validation Engine"
(rediseno "AI Editor Runtime", 2026-08-11), Nivel 1 (sintaxis). Aislados:
usan `tmp_path` con archivos sinteticos. La prueba contra un sandbox real
(incluida la deteccion de un error de sintaxis Python real inyectado)
vive en test_pipeline_equivalence.py.
"""
from ai_editor.validation import LEVELS_2_TO_5_REASON, check_syntax, run_validation


def test_valid_python_file_passes(tmp_path):
    (tmp_path / "ok.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    ok, detail = check_syntax(tmp_path, "ok.py")
    assert ok is True
    assert "valida" in detail


def test_invalid_python_file_fails_with_syntax_error_detail(tmp_path):
    (tmp_path / "bad.py").write_text("def f(:\n    return 1\n", encoding="utf-8")
    ok, detail = check_syntax(tmp_path, "bad.py")
    assert ok is False
    assert "SyntaxError" in detail


def test_valid_js_file_passes(tmp_path):
    (tmp_path / "ok.js").write_text("function f() { return 1; }\n", encoding="utf-8")
    ok, detail = check_syntax(tmp_path, "ok.js")
    assert ok is True


def test_invalid_js_file_fails(tmp_path):
    (tmp_path / "bad.js").write_text("function f( { return 1; }\n", encoding="utf-8")
    ok, detail = check_syntax(tmp_path, "bad.js")
    assert ok is False


def test_vue_file_with_valid_script_block_passes(tmp_path):
    (tmp_path / "ok.vue").write_text(
        "<template><div>{{ x }}</div></template>\n"
        "<script>\nexport default { data() { return { x: 1 }; } };\n</script>\n",
        encoding="utf-8",
    )
    ok, detail = check_syntax(tmp_path, "ok.vue")
    assert ok is True


def test_vue_file_with_broken_script_block_fails(tmp_path):
    (tmp_path / "bad.vue").write_text(
        "<template><div></div></template>\n<script>\nfunction f( {\n</script>\n",
        encoding="utf-8",
    )
    ok, detail = check_syntax(tmp_path, "bad.vue")
    assert ok is False


def test_vue_file_without_script_block_passes_trivially(tmp_path):
    (tmp_path / "template_only.vue").write_text("<template><div></div></template>\n", encoding="utf-8")
    ok, detail = check_syntax(tmp_path, "template_only.vue")
    assert ok is True
    assert "sin bloque" in detail


def test_unknown_extension_is_skipped_not_failed(tmp_path):
    (tmp_path / "data.json").write_text("{not valid json at all", encoding="utf-8")
    ok, detail = check_syntax(tmp_path, "data.json")
    assert ok is True
    assert "omitido" in detail


def test_missing_file_is_treated_as_nothing_to_validate(tmp_path):
    ok, detail = check_syntax(tmp_path, "does/not/exist.py")
    assert ok is True


def test_run_validation_aggregates_across_all_plan_steps(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def f(:\n", encoding="utf-8")

    class _FakeSandbox:
        root = tmp_path

    plan = {
        "steps": [
            {"file": "a.py"}, {"file": "b.py"}, {"file": "a.py"},  # duplicado, no doble-cuenta
        ],
    }

    report = run_validation(_FakeSandbox(), plan)

    assert set(report.level_1_syntax.keys()) == {"a.py", "b.py"}
    assert report.level_1_syntax["a.py"]["ok"] is True
    assert report.level_1_syntax["b.py"]["ok"] is False
    assert report.level_1_passed is False


def test_levels_2_to_5_are_explicitly_not_implemented_not_faked(tmp_path):
    class _FakeSandbox:
        root = tmp_path

    report = run_validation(_FakeSandbox(), {"steps": []})

    assert report.levels_2_to_5_status == "NOT_IMPLEMENTED"
    assert "sandbox" in report.levels_2_to_5_reason.lower()
    assert report.levels_2_to_5_reason == LEVELS_2_TO_5_REASON
