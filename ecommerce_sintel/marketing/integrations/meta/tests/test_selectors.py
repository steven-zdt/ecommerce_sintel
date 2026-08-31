from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketing.integrations.meta.exceptions import MetaConfigError
from marketing.services.meta_selectors import MetaCampaignSelector


class MetaCampaignSelectorTests(SimpleTestCase):

    @patch("marketing.services.meta_selectors.MetaMarketingClient")
    def test_get_campaigns_keeps_budget_in_minor_units(self, mock_cls):
        mock_cls.return_value.list_campaigns.return_value = [
            {"id": "c1", "name": "BF", "status": "ACTIVE", "daily_budget": "500000"},
        ]
        out = MetaCampaignSelector.get_campaigns()
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["campaigns"][0]["daily_budget_minor"], 500000)
        self.assertEqual(out["campaigns"][0]["name"], "BF")

    @patch("marketing.services.meta_selectors.MetaMarketingClient")
    def test_get_insights_flattens_purchase_roas_list(self, mock_cls):
        mock_cls.return_value.get_insights.return_value = [
            {"campaign_id": "c1", "spend": "10.0", "purchase_roas": [{"action_type": "omni_purchase", "value": "3.4"}]},
        ]
        out = MetaCampaignSelector.get_insights(object_id="c1")
        self.assertEqual(out["rows"][0]["purchase_roas"], 3.4)
        self.assertEqual(out["rows"][0]["spend"], 10.0)

    @patch("marketing.services.meta_selectors.MetaMarketingClient")
    def test_config_error_propagates_untouched(self, mock_cls):
        mock_cls.return_value.list_campaigns.side_effect = MetaConfigError("META_AD_ACCOUNT_ID no configurado.")
        with self.assertRaises(MetaConfigError):
            MetaCampaignSelector.get_campaigns()

    @patch("marketing.services.meta_selectors.MetaMarketingClient")
    def test_account_summary_merges_account_info_and_insights(self, mock_cls):
        mock_cls.return_value.get_account_info.return_value = {
            "name": "SINTEL Ads", "currency": "COP", "amount_spent": "1200000",
        }
        mock_cls.return_value.get_account_summary.return_value = {"spend": "50000", "clicks": "10"}
        out = MetaCampaignSelector.get_account_summary()
        self.assertEqual(out["account"]["currency"], "COP")
        self.assertEqual(out["account"]["amount_spent_minor"], 1200000)
        self.assertEqual(out["summary"]["spend"], 50000)

    @patch("marketing.services.meta_selectors.MetaMarketingClient")
    def test_account_summary_empty_when_no_insight_rows(self, mock_cls):
        mock_cls.return_value.get_account_info.return_value = {"currency": "USD"}
        mock_cls.return_value.get_account_summary.return_value = {}
        out = MetaCampaignSelector.get_account_summary()
        self.assertEqual(out["summary"], {})
