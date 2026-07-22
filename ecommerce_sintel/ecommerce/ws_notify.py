import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

def ws_notify(group, event_type, payload):
    """
    Utility to send a message to a WebSocket group.
    Standardized to be called from the service layer.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning(f"[ws_notify] No channel layer available for group {group}")
        return

    try:
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": event_type,
                "payload": payload,
            }
        )
    except Exception as e:
        logger.error(f"[ws_notify] Error sending to group {group}: {str(e)}")
