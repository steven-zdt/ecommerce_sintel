"""
MetaCampaignSelector -- lectura normalizada de Meta Ads para consumo interno
(dashboard admin y endpoints internal_ai del ai_engine).

FASE 7 del plan de integracion Meta Business
(Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).

Responsabilidad: llamar a MetaMarketingClient y devolver estructuras estables
y planas (nombres de campo consistentes, numeros como numeros). NO decide
HTTP status ni maneja permisos -- eso vive en las vistas
(marketing/api/internal_ai.py, dashboard). Las excepciones tipadas de la
frontera Meta (MetaConfigError / MetaAuthError / MetaApiTransientError /
MetaApiError) se propagan tal cual: cada vista las mapea a su status.

SOLO LECTURA. Ningun metodo aqui escribe en Meta.
"""
from marketing.integrations.meta.marketing import MetaMarketingClient


def _num(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _amount_minor(value):
    """daily_budget / lifetime_budget de Meta vienen en la unidad MINIMA de la
    moneda de la cuenta (para USD centavos; para COP, que no tiene decimales, el
    propio peso). Se devuelve el valor crudo como entero -- convertir a unidad
    mayor requiere saber los decimales de la moneda (campo `currency` de la
    cuenta), y eso es responsabilidad de quien formatea (dashboard FASE 8), no de
    este selector."""
    return _num(value)


def _normalize_campaign(c: dict) -> dict:
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "status": c.get("status"),
        "effective_status": c.get("effective_status"),
        "objective": c.get("objective"),
        "daily_budget_minor": _amount_minor(c.get("daily_budget")),
        "lifetime_budget_minor": _amount_minor(c.get("lifetime_budget")),
        "budget_remaining_minor": _amount_minor(c.get("budget_remaining")),
        "start_time": c.get("start_time"),
        "stop_time": c.get("stop_time"),
        "created_time": c.get("created_time"),
        "updated_time": c.get("updated_time"),
    }


def _normalize_insight(row: dict) -> dict:
    roas = row.get("purchase_roas")
    if isinstance(roas, list):
        roas = roas[0].get("value") if roas else None
    return {
        "campaign_id": row.get("campaign_id"),
        "campaign_name": row.get("campaign_name"),
        "adset_id": row.get("adset_id"),
        "ad_id": row.get("ad_id"),
        "impressions": _num(row.get("impressions")),
        "clicks": _num(row.get("clicks")),
        "spend": _num(row.get("spend")),
        "ctr": _num(row.get("ctr")),
        "cpc": _num(row.get("cpc")),
        "cpm": _num(row.get("cpm")),
        "reach": _num(row.get("reach")),
        "frequency": _num(row.get("frequency")),
        "purchase_roas": _num(roas),
        "actions": row.get("actions") or [],
    }


class MetaCampaignSelector:

    @staticmethod
    def _client() -> MetaMarketingClient:
        return MetaMarketingClient()

    @staticmethod
    def get_campaigns(*, effective_status: list[str] | None = None, limit: int = 50) -> dict:
        raw = MetaCampaignSelector._client().list_campaigns(
            limit=limit, effective_status=effective_status,
        )
        campaigns = [_normalize_campaign(c) for c in raw]
        return {"count": len(campaigns), "campaigns": campaigns}

    @staticmethod
    def get_campaign_detail(campaign_id: str) -> dict:
        client = MetaCampaignSelector._client()
        campaign = _normalize_campaign(client.get_campaign(campaign_id))
        adsets = client.list_adsets(campaign_id)
        insights = [_normalize_insight(r) for r in client.get_insights(campaign_id, level="campaign")]
        return {
            "campaign": campaign,
            "adsets": [
                {
                    "id": a.get("id"), "name": a.get("name"),
                    "status": a.get("status"), "effective_status": a.get("effective_status"),
                    "daily_budget_minor": _amount_minor(a.get("daily_budget")),
                    "optimization_goal": a.get("optimization_goal"),
                }
                for a in adsets
            ],
            "insights": insights,
        }

    @staticmethod
    def get_insights(*, object_id: str, level: str = "campaign",
                     date_preset: str = "last_30d", time_range: dict | None = None) -> dict:
        rows = MetaCampaignSelector._client().get_insights(
            object_id, level=level, date_preset=date_preset, time_range=time_range,
        )
        return {
            "object_id": object_id,
            "level": level,
            "period": time_range or {"date_preset": date_preset},
            "rows": [_normalize_insight(r) for r in rows],
        }

    @staticmethod
    def get_account_summary(*, date_preset: str = "last_30d") -> dict:
        client = MetaCampaignSelector._client()
        info = client.get_account_info()
        summary = client.get_account_summary(date_preset=date_preset)
        return {
            "period": {"date_preset": date_preset},
            "account": {
                "name": info.get("name"),
                "currency": info.get("currency"),
                "timezone_name": info.get("timezone_name"),
                "account_status": info.get("account_status"),
                "amount_spent_minor": _num(info.get("amount_spent")),
            },
            "summary": _normalize_insight(summary) if summary else {},
        }
