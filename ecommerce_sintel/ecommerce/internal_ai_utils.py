"""
ecommerce/internal_ai_utils.py

Shared utility for internal AI endpoint audit logging.
All internal_ai.py modules should import log_ai_action from here
instead of defining their own _log_ai_action copy.
"""


def log_ai_action(request, tool: str, metadata: dict) -> None:
    """
    Log an AI-triggered write action to the SecurityEvent audit trail.

    Usage:
        from ecommerce.internal_ai_utils import log_ai_action
        log_ai_action(request, 'MyTool', {'uuid': str(obj.uuid)})
    """
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands

    SecurityCommands.log_event(
        SecurityEvent.AI_ACTION_EXECUTED,
        request=request,
        metadata={'tool': tool, **metadata},
    )
