"""
Unit tests puros (sin I/O) para Node/Edge/KnowledgeGraph. Fase 15,
PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08.
"""
from project_knowledge_graph.knowledge_graph.relations import KnowledgeGraph, Node


def _build_chain_graph() -> KnowledgeGraph:
    """A -> B -> C (DEPENDS_ON), usado por varios tests de vecindario/transitividad."""
    kg = KnowledgeGraph()
    kg.add_node(Node("a", "Model", "A"))
    kg.add_node(Node("b", "Model", "B"))
    kg.add_node(Node("c", "Model", "C"))
    kg.add_edge("a", "b", "DEPENDS_ON")
    kg.add_edge("b", "c", "DEPENDS_ON")
    return kg


def test_add_node_is_idempotent():
    kg = KnowledgeGraph()
    kg.add_node(Node("a", "Model", "A"))
    kg.add_node(Node("a", "Model", "A-duplicada-se-ignora"))
    assert len(kg.nodes) == 1
    assert kg.nodes["a"].name == "A"


def test_add_edge_dedupes_and_requires_both_endpoints():
    kg = KnowledgeGraph()
    kg.add_node(Node("a", "Model", "A"))
    kg.add_node(Node("b", "Model", "B"))
    kg.add_edge("a", "b", "DEPENDS_ON")
    kg.add_edge("a", "b", "DEPENDS_ON")  # duplicado exacto, no debe agregar
    kg.add_edge("a", "ghost", "DEPENDS_ON")  # target no existe, no debe agregar
    assert len(kg.edges) == 1


def test_what_depends_on_and_what_this_uses_are_inverses():
    kg = _build_chain_graph()
    assert kg.what_this_uses("a") == ["b"]
    assert kg.what_depends_on("b") == ["a"]
    assert kg.what_depends_on("c") == ["b"]


def test_transitive_dependents_follows_the_full_chain():
    kg = _build_chain_graph()
    # Si C cambia, B depende de C, y A depende de B (transitivamente) -- ambos afectados.
    assert kg.transitive_dependents("c") == {"a", "b"}


def test_transitive_dependents_respects_max_depth():
    kg = _build_chain_graph()
    assert kg.transitive_dependents("c", max_depth=1) == {"b"}


def test_neighborhood_bfs_includes_both_directions():
    kg = _build_chain_graph()
    neigh = kg.neighborhood("b", depth=1)
    node_ids = {n["id"] for n in neigh["nodes"]}
    assert node_ids == {"b", "a", "c"}


def test_find_by_name_is_case_insensitive_substring():
    kg = _build_chain_graph()
    assert [n.id for n in kg.find_by_name("a")] == ["a"]  # "A".lower() == "a" contiene "a"
    assert kg.find_by_name("nonexistent") == []


def test_to_dict_from_dict_roundtrip_preserves_graph():
    kg = _build_chain_graph()
    data = kg.to_dict()
    restored = KnowledgeGraph.from_dict(data)
    assert set(restored.nodes.keys()) == set(kg.nodes.keys())
    assert len(restored.edges) == len(kg.edges)
    assert restored.what_depends_on("b") == ["a"]


def test_to_dict_stats_match_actual_counts():
    kg = _build_chain_graph()
    stats = kg.to_dict()["stats"]
    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 2
    assert stats["node_types"] == {"Model": 3}
