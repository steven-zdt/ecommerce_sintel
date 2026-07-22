import logging

from security.models import SecurityEvent

logger = logging.getLogger(__name__)


class SecurityCommands:
    """
    Unico punto de entrada para registrar eventos de seguridad -- mismo patron
    que notifications.services.commands.NotificationCommands.dispatch_notification:
    las demas apps importan SecurityCommands de forma diferida (dentro del
    metodo que lo llama) y nunca escriben en SecurityEvent directamente.
    """

    @staticmethod
    def log_event(event_type, request=None, user=None, severity=SecurityEvent.SEVERITY_INFO, metadata=None):
        """
        Nunca debe romper el flujo de negocio del caller: si el logging mismo
        falla (ej. metadata no serializable), se traga el error y solo se deja
        constancia en el logger de Django.
        """
        try:
            resolved_user = user
            if resolved_user is None and request is not None:
                req_user = getattr(request, 'user', None)
                if req_user is not None and getattr(req_user, 'is_authenticated', False):
                    resolved_user = req_user

            SecurityEvent.objects.create(
                event_type=event_type,
                severity=severity,
                user=resolved_user,
                ip_address=request.META.get('REMOTE_ADDR') if request is not None else None,
                user_agent=(request.META.get('HTTP_USER_AGENT', '') if request is not None else '')[:255],
                path=(request.path if request is not None else '')[:255],
                metadata=metadata or {},
            )
        except Exception:
            logger.exception('[security:log_event] fallo al registrar %s', event_type)
