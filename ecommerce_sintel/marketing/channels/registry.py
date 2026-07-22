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


def get_adapter(channel_name: str):
    """Returns an instantiated adapter for the given channel name."""
    adapter_class = CHANNEL_REGISTRY.get(channel_name)
    if not adapter_class:
        raise ValueError(f"Canal desconocido: '{channel_name}'. Disponibles: {AVAILABLE_CHANNELS}")
    return adapter_class()
