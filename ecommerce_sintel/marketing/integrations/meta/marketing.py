"""
MetaMarketingClient -- lectura de la Marketing API de Meta (campanas, adsets,
ads, creativos, insights), construido sobre MetaGraphClient.

FASE 7 del plan de integracion Meta Business
(Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).

SOLO LECTURA en esta fase -- ningun metodo hace POST/DELETE. Las escrituras
(pause/resume/budget/create) llegan en las FASE 16-18, detras de la Policy Layer
y aprobacion humana.
"""
import json
import logging

from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import MetaConfigError

logger = logging.getLogger(__name__)

_CAMPAIGN_FIELDS = (
    "id,name,status,effective_status,objective,daily_budget,lifetime_budget,"
    "budget_remaining,start_time,stop_time,created_time,updated_time"
)
_ADSET_FIELDS = (
    "id,name,status,effective_status,campaign_id,daily_budget,lifetime_budget,"
    "optimization_goal,billing_event,start_time,end_time"
)
_AD_FIELDS = "id,name,status,effective_status,adset_id,campaign_id,creative"
_INSIGHT_FIELDS = (
    "campaign_id,campaign_name,adset_id,adset_name,ad_id,ad_name,impressions,"
    "clicks,spend,ctr,cpc,cpm,reach,frequency,actions,action_values,purchase_roas"
)
_ACCOUNT_INSIGHT_FIELDS = (
    "impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,purchase_roas,actions,action_values"
)

_MAX_PAGES = 5


class MetaMarketingClient:

    def __init__(self, *, graph: MetaGraphClient | None = None):
        self._graph = graph or MetaGraphClient()
        self._ad_account_id = (self._graph._settings.get("meta_ad_account_id", "") or "").strip()

    def _act(self) -> str:
        if not self._ad_account_id:
            raise MetaConfigError("META_AD_ACCOUNT_ID no configurado (numero sin 'act_').")
        # Meta acepta el id con o sin 'act_'; se normaliza aqui.
        acc = self._ad_account_id
        return acc if acc.startswith("act_") else f"act_{acc}"

    # -- campanas / adsets / ads --------------------------------------------

    def list_campaigns(self, *, limit: int = 50, effective_status: list[str] | None = None) -> list[dict]:
        params = {"fields": _CAMPAIGN_FIELDS, "limit": limit}
        if effective_status:
            params["effective_status"] = json.dumps(list(effective_status))
        return list(self._graph.paginate(f"/{self._act()}/campaigns", params=params, max_pages=_MAX_PAGES))

    def get_campaign(self, campaign_id: str) -> dict:
        return self._graph.get(f"/{campaign_id}", params={"fields": _CAMPAIGN_FIELDS})

    def list_adsets(self, campaign_id: str, *, limit: int = 50) -> list[dict]:
        params = {"fields": _ADSET_FIELDS, "limit": limit}
        return list(self._graph.paginate(f"/{campaign_id}/adsets", params=params, max_pages=_MAX_PAGES))

    def list_ads(self, adset_id: str, *, limit: int = 50) -> list[dict]:
        params = {"fields": _AD_FIELDS, "limit": limit}
        return list(self._graph.paginate(f"/{adset_id}/ads", params=params, max_pages=_MAX_PAGES))

    # -- insights ----------------------------------------------------------

    def get_insights(self, object_id: str, *, level: str = "campaign",
                     date_preset: str = "last_30d", time_range: dict | None = None) -> list[dict]:
        """Insights de un objeto (campaign/adset/ad) o del propio ad account.
        `time_range` (dict {'since','until'} YYYY-MM-DD) tiene prioridad sobre
        `date_preset`."""
        params = {"fields": _INSIGHT_FIELDS, "level": level}
        if time_range:
            params["time_range"] = json.dumps(time_range)
        else:
            params["date_preset"] = date_preset
        return list(self._graph.paginate(f"/{object_id}/insights", params=params, max_pages=_MAX_PAGES))

    def get_account_info(self) -> dict:
        """Datos de la cuenta publicitaria. `currency` es necesario para
        interpretar los presupuestos (unidad minima -> decimales de la moneda)."""
        return self._graph.get(
            f"/{self._act()}",
            params={"fields": "name,currency,timezone_name,account_status,amount_spent,balance"},
        )

    def get_account_summary(self, *, date_preset: str = "last_30d") -> dict:
        data = self._graph.get(
            f"/{self._act()}/insights",
            params={"fields": _ACCOUNT_INSIGHT_FIELDS, "level": "account", "date_preset": date_preset},
        )
        rows = data.get("data", [])
        return rows[0] if rows else {}
