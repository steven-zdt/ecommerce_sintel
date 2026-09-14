"""FASE 10 integracion Meta Business: registro de servidores MCP."""
from mcp_client.registry import MCPServerRegistry


def test_meta_ads_server_is_registered():
    srv = MCPServerRegistry.get("meta_ads")
    assert srv is not None
    assert srv.url.startswith("https://")
    assert "facebook.com" in srv.url


def test_unknown_server_is_none():
    assert MCPServerRegistry.get("nope") is None


def test_writes_disabled_by_default():
    # FASE 10 -- MCP_META_ADS_ALLOW_WRITES default False.
    assert MCPServerRegistry.get("meta_ads").allow_writes is False


def test_list_enabled_is_subset_of_all():
    all_keys = {s.key for s in MCPServerRegistry.list_all()}
    enabled_keys = {s.key for s in MCPServerRegistry.list_enabled()}
    assert enabled_keys <= all_keys
