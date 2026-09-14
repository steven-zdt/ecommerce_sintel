"""
Unit tests para audit/query_log.py -- Fase 18 "Observability", Site
Knowledge Graph, 2026-08-10. Aislados con un archivo de log temporal (no
tocan QUERY_AUDIT_LOG_PATH real); la prueba de que graph_sdk realmente
llama a `log_query()` para cada una de las 13 operaciones, contra el
grafo real, vive en test_pipeline_equivalence.py.
"""
import json

import pytest

from project_knowledge_graph.audit import query_log


@pytest.fixture()
def temp_log_path(tmp_path, monkeypatch):
    path = tmp_path / "QUERY_AUDIT_LOG.jsonl"
    monkeypatch.setattr(query_log, "QUERY_AUDIT_LOG_PATH", path)
    return path


def test_log_query_never_persists_full_meta(temp_log_path):
    """Solo campos top-level (found/name/tipo/listas top-level) se
    persisten -- `meta` (o cualquier dict anidado) nunca se serializa tal
    cual, sea cual sea su contenido. Mismo criterio que
    `calculate_change_impact()` real: `direct_impact`/`indirect_impact`
    son dicts anidados por categoria, no listas top-level -- no se
    cuentan (limite deliberado, evita recursion sin fin sobre resultados
    arbitrariamente anidados); `recommended_order` SI es una lista
    top-level real, esa si se cuenta."""
    result = {
        "found": True,
        "name": "SomeEndpoint",
        "meta": {"secret_looking_field": "should-never-appear-in-log"},
        "direct_impact": {"contract": [{"name": "a"}, {"name": "b"}]},
        "recommended_order": ["1. Domain", "2. Contract", "3. Frontend"],
    }
    query_log.log_query("resolve_change", ("SomeEndpoint",), {}, result, 12.3, "2026-08-10T00:00:00Z")

    record = json.loads(temp_log_path.read_text(encoding="utf-8").strip())
    assert "secret_looking_field" not in json.dumps(record)
    assert record["result"]["found"] is True
    assert record["result"]["name"] == "SomeEndpoint"
    assert "direct_impact" not in record["result"]
    assert "direct_impact_count" not in record["result"]
    assert record["result"]["recommended_order_count"] == 3


def test_log_query_truncates_long_string_args(temp_log_path):
    long_arg = "x" * 500
    query_log.log_query("find_docs", (long_arg,), {}, {"found": False}, 1.0, None)

    record = json.loads(temp_log_path.read_text(encoding="utf-8").strip())
    assert len(record["args"][0]) <= query_log.MAX_ARG_LEN + len("...(truncado)")
    assert record["args"][0].endswith("...(truncado)")


def test_log_query_is_best_effort_on_write_failure(monkeypatch):
    class _UnwritablePath:
        def open(self, *a, **k):
            raise OSError("disk full (simulado)")

    monkeypatch.setattr(query_log, "QUERY_AUDIT_LOG_PATH", _UnwritablePath())
    # No debe lanzar -- una consulta real nunca deberia fallar por un
    # problema de logging.
    query_log.log_query("find_symbol", ("X",), {}, {"found": False}, 1.0, None)


def test_read_recent_queries_respects_limit_and_skips_corrupt_lines(temp_log_path):
    lines = [json.dumps({"operation": f"op{i}"}) for i in range(5)]
    lines.insert(2, "{not valid json")
    temp_log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    records = query_log.read_recent_queries(limit=3)
    assert len(records) == 3
    assert [r["operation"] for r in records] == ["op2", "op3", "op4"]


def test_read_recent_queries_returns_empty_list_when_no_log_file(temp_log_path):
    assert query_log.read_recent_queries() == []
