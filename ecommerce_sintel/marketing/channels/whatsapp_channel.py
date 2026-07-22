"""
WhatsApp Channel Adapter
Uses Meta Cloud API to send messages via approved templates.
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class WhatsAppChannelAdapter(AbstractChannelAdapter):
    channel_name = "whatsapp"

    BASE_URL = "https://graph.facebook.com/v19.0"

    def send(self, message: CampaignMessage) -> dict:
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md. NOTA: notifications/clients/whatsapp.py
        # (envio transaccional, distinto de este canal de campanas) sigue leyendo settings
        # directo -- migrarlo queda fuera del alcance de "Marketing" como consumidor.
        from organization.services.selectors import OrganizationSelector
        integrations = OrganizationSelector.get_integration_settings()
        phone_number_id = integrations['whatsapp_phone_number_id']
        token = integrations['meta_access_token']
        url = f"{self.BASE_URL}/{phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "to": message.recipient,
            "type": "template",
            "template": {
                "name": "marketing_campaign",   # Must be a pre-approved template in Meta Business Manager
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": message.body[:1024]}]
                    }
                ]
            }
        }

        try:
            response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=10)
            response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
