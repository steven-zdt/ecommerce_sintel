"""FASE 10 integracion Meta Business: clasificacion de tools MCP."""
from mcp_client.policy import classify_mcp_tool


class TestClassifyMcpToolReadOnly:
    """allow_writes=False (FASE 10): solo lectura clara pasa."""

    def test_get_and_list_are_allowed(self):
        assert classify_mcp_tool("meta_ads", "get_campaigns", allow_writes=False) == "allow"
        assert classify_mcp_tool("meta_ads", "list_ad_accounts", allow_writes=False) == "allow"
        assert classify_mcp_tool("meta_ads", "search_audiences", allow_writes=False) == "allow"
        assert classify_mcp_tool("meta_ads", "get_campaign_insights", allow_writes=False) == "allow"

    def test_writes_are_denied(self):
        for name in ("create_campaign", "update_adset_budget", "pause_campaign",
                     "delete_ad", "duplicate_campaign", "upload_ad_creative"):
            assert classify_mcp_tool("meta_ads", name, allow_writes=False) == "deny"

    def test_unknown_verb_is_denied(self):
        assert classify_mcp_tool("meta_ads", "reticulate_splines", allow_writes=False) == "deny"

    def test_empty_name_is_denied(self):
        assert classify_mcp_tool("meta_ads", "", allow_writes=False) == "deny"


class TestClassifyMcpToolWritesEnabled:
    """allow_writes=True (FASE 16+): writes -> confirm, dinero/cuenta -> deny."""

    def test_reads_still_allowed(self):
        assert classify_mcp_tool("meta_ads", "get_campaigns", allow_writes=True) == "allow"

    def test_known_writes_require_confirm(self):
        assert classify_mcp_tool("meta_ads", "pause_campaign", allow_writes=True) == "confirm"
        assert classify_mcp_tool("meta_ads", "update_adset_budget", allow_writes=True) == "confirm"

    def test_money_and_account_tools_always_denied(self):
        for name in ("update_billing_info", "get_invoice", "set_payment_method",
                     "update_spend_cap", "delete_account", "transfer_funds"):
            assert classify_mcp_tool("meta_ads", name, allow_writes=True) == "deny"
