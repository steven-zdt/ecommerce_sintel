"""
Unit tests para ai_editor/resolver/ -- POST-GRAPH 3 "Change Resolver"
(rediseno "AI Editor Runtime", 2026-08-11). Aislados: mockean
`ai_editor.graph_client` para no depender del grafo real; la prueba de
priorizacion EXACTO/FUZZY contra datos reales (el caso 'Equipment' que
motivo el fix) vive en test_pipeline_equivalence.py.
"""
from unittest.mock import patch

from ai_editor.intent.schema import ChangeIntent
from ai_editor.resolver import (
    STATUS_PARTIALLY_RESOLVED,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    resolve_change_context,
)


def _intent(**overrides) -> ChangeIntent:
    defaults = dict(
        id="t", request="r", domain="shop", intent="modify",
        entities=[], scope=[], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    defaults.update(overrides)
    return ChangeIntent(**defaults)


def test_needs_clarification_intent_short_circuits_to_unresolved():
    """No gasta ninguna consulta al grafo sobre una intencion que la fase
    anterior (POST-GRAPH 2) ya marco como no confiable."""
    intent = _intent(status="NEEDS_CLARIFICATION", entities=["X"])
    with patch("ai_editor.resolver.resolver.graph_client") as mock_client:
        ctx = resolve_change_context(intent)
    mock_client.find_node.assert_not_called()
    assert ctx.status == STATUS_UNRESOLVED
    assert ctx.unresolved_entities == ["X"]


def test_falls_back_to_domain_when_no_entities_given():
    intent = _intent(domain="shop", entities=[])
    with patch("ai_editor.resolver.resolver.graph_client") as mock_client:
        mock_client.find_node.return_value = {"id": "app:shop", "type": "App", "name": "shop"}
        mock_client.resolve_change.return_value = {"found": True, "target": {"id": "app:shop"}}
        mock_client.build_context_packet.return_value = {"found": True, "stats": {}}

        ctx = resolve_change_context(intent)

    mock_client.find_node.assert_called_once_with("shop")
    assert ctx.status == STATUS_RESOLVED
    assert ctx.primary_target["id"] == "app:shop"


def test_no_candidates_resolve_returns_unresolved_without_fabricating():
    intent = _intent(entities=["NonExistentThing"])
    with patch("ai_editor.resolver.resolver.graph_client") as mock_client:
        mock_client.find_node.return_value = None

        ctx = resolve_change_context(intent)

    assert ctx.status == STATUS_UNRESOLVED
    assert ctx.primary_target is None
    mock_client.resolve_change.assert_not_called()
    mock_client.build_context_packet.assert_not_called()


def test_symbol_type_wins_priority_over_model_when_both_resolve_exactly():
    intent = _intent(entities=["SomeModel", "SomeViewSet.action"])
    with patch("ai_editor.resolver.resolver.graph_client") as mock_client:
        def _find_node(name):
            return {
                "SomeModel": {"id": "model:x:SomeModel", "type": "Model", "name": "SomeModel"},
                "SomeViewSet.action": {"id": "symbol:x:SomeViewSet.action", "type": "Symbol", "name": "SomeViewSet.action"},
            }[name]
        mock_client.find_node.side_effect = _find_node
        mock_client.resolve_change.return_value = {"found": True, "target": {"id": "symbol:x:SomeViewSet.action"}}
        mock_client.build_context_packet.return_value = {"found": True, "stats": {}}

        ctx = resolve_change_context(intent)

    assert ctx.primary_target["type"] == "Symbol"
    assert ctx.resolved_entities[0]["type"] == "Model"
    assert ctx.status == STATUS_RESOLVED


def test_partially_resolved_when_some_entities_confirm_and_others_dont():
    intent = _intent(entities=["RealThing", "FakeThing"])
    with patch("ai_editor.resolver.resolver.graph_client") as mock_client:
        def _find_node(name):
            if name == "RealThing":
                return {"id": "model:x:RealThing", "type": "Model", "name": "RealThing"}
            return None
        mock_client.find_node.side_effect = _find_node
        mock_client.resolve_change.return_value = {"found": True, "target": {"id": "model:x:RealThing"}}
        mock_client.build_context_packet.return_value = {"found": True, "stats": {}}

        ctx = resolve_change_context(intent)

    assert ctx.status == STATUS_PARTIALLY_RESOLVED
    assert ctx.unresolved_entities == ["'FakeThing': no se encontro ningun nodo en el grafo"]
