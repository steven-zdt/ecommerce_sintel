"""
Unit tests para incremental/diff.py::parse_diff_hunks -- Fase 15
"Incremental Semantic Graph", Site Knowledge Graph, 2026-08-10. La prueba
contra el repo real (cruzar un hunk sintetico contra un Symbol REAL del
grafo ya construido, verificando que se identifica exactamente
`EquipmentViewSet.check_availability`) vive en test_pipeline_equivalence.py.
"""
from project_knowledge_graph.incremental.diff import parse_diff_hunks


def test_parse_diff_hunks_extracts_new_side_line_range():
    diff_text = (
        "diff --git a/ecommerce_sintel/renting/api/views.py b/ecommerce_sintel/renting/api/views.py\n"
        "--- a/ecommerce_sintel/renting/api/views.py\n"
        "+++ b/ecommerce_sintel/renting/api/views.py\n"
        "@@ -155,3 +155,4 @@\n"
        "+    pass\n"
    )
    hunks = parse_diff_hunks(diff_text)
    assert hunks == [{"file": "ecommerce_sintel/renting/api/views.py", "start_line": 155, "end_line": 158}]


def test_parse_diff_hunks_handles_multiple_files():
    diff_text = (
        "+++ b/ecommerce_sintel/shop/models.py\n"
        "@@ -10,0 +11,2 @@\n"
        "+++ b/ecommerce_sintel/renting/api/views.py\n"
        "@@ -200,1 +201,1 @@\n"
    )
    hunks = parse_diff_hunks(diff_text)
    assert hunks == [
        {"file": "ecommerce_sintel/shop/models.py", "start_line": 11, "end_line": 12},
        {"file": "ecommerce_sintel/renting/api/views.py", "start_line": 201, "end_line": 201},
    ]


def test_parse_diff_hunks_skips_pure_deletion_hunks():
    """`+0,0` significa que el lado nuevo no tiene ninguna linea (borrado
    puro) -- no hay simbolo "actual" que cruzar, no deberia generar hunk."""
    diff_text = "+++ b/ecommerce_sintel/shop/models.py\n@@ -10,3 +10,0 @@\n"
    assert parse_diff_hunks(diff_text) == []


def test_parse_diff_hunks_default_count_is_one():
    """`@@ -a +c @@` sin `,count` significa 1 linea (convencion real de
    unified diff)."""
    diff_text = "+++ b/ecommerce_sintel/shop/models.py\n@@ -5 +5 @@\n"
    hunks = parse_diff_hunks(diff_text)
    assert hunks == [{"file": "ecommerce_sintel/shop/models.py", "start_line": 5, "end_line": 5}]
