"""
Channel Registry
Maps channel names to their adapter classes.
Add new adapters here to extend the system.
"""
from marketing.channels.email_channel import EmailChannelAdapter
from marketing.channels.whatsapp_channel import WhatsAppChannelAdapter
from marketing.channels.facebook_channel import FacebookChannelAdapter
from marketing.channels.instagram_channel import InstagramChannelAdapter
from marketing.channels.youtube_channel import YouTubeChannelAdapter
from marketing.channels.tiktok_channel import TikTokChannelAdapter
from marketing.channels.x_channel import XChannelAdapter
from marketing.channels.google_business_channel import GoogleBusinessChannelAdapter

CHANNEL_REGISTRY = {
    "email": EmailChannelAdapter,
    "whatsapp": WhatsAppChannelAdapter,
    "facebook": FacebookChannelAdapter,
    "instagram": InstagramChannelAdapter,
    "youtube": YouTubeChannelAdapter,
    "tiktok": TikTokChannelAdapter,
    "x": XChannelAdapter,
    "google_business": GoogleBusinessChannelAdapter,
}

AVAILABLE_CHANNELS = list(CHANNEL_REGISTRY.keys())

# Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): facebook/instagram/youtube/tiktok/
# x/google_business ignoran CampaignMessage.recipient (publican a nivel de pagina/cuenta, no a
# un destinatario individual) -- son los unicos canales que el agente autonomo
# (marketing/agent/brain.py) puede despachar de forma segura con su sentinel "broadcast", ya que
# no resuelve una lista real de destinatarios por usuario. email/whatsapp SI usan `recipient`
# como direccion real (email.to=[...], whatsapp "to": ...) y antes rompian en silencio (fallaban
# siempre, CampaignLog.is_sent=False) cuando el LLM los elegia.
BROADCAST_CHANNELS = {
    'facebook', 'instagram', 'youtube', 'tiktok', 'x', 'google_business',
}


def get_adapter(channel_name: str):
    """Returns an instantiated adapter for the given channel name."""
    adapter_class = CHANNEL_REGISTRY.get(channel_name)
    if not adapter_class:
        raise ValueError(f"Canal desconocido: '{channel_name}'. Disponibles: {AVAILABLE_CHANNELS}")
    return adapter_class()
