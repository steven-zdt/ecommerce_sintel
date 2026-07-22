"""
Base Channel Adapter
Defines the contract that all marketing channel adapters must implement.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CampaignMessage:
    """Unified message structure for all channels."""
    recipient: str          # email, phone, page_id, etc.
    subject: str            # Used for email. Becomes post title for social.
    body: str               # Main content
    media_url: Optional[str] = None  # Image/video URL for social posts


class AbstractChannelAdapter(ABC):
    """
    Adapter interface for all marketing channels.
    Each channel implements send() independently.
    """
    channel_name: str = "base"

    @abstractmethod
    def send(self, message: CampaignMessage) -> dict:
        """
        Send a message through the channel.
        Returns: dict with keys: success (bool), channel, response (str)
        """
        raise NotImplementedError
