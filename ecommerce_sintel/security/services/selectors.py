from django.core.cache import cache
from django.db import connection

from security.models import SecurityEvent


class SecuritySelector:

    @staticmethod
    def list_events(event_type=None, severity=None, user_uuid=None):
        qs = SecurityEvent.objects.select_related('user').all()
        if event_type:
            qs = qs.filter(event_type=event_type)
        if severity:
            qs = qs.filter(severity=severity)
        if user_uuid:
            qs = qs.filter(user__uuid=user_uuid)
        return qs

    @staticmethod
    def get_health_snapshot():
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        redis_ok = True
        try:
            cache.set('security_health_check', '1', timeout=5)
            redis_ok = cache.get('security_health_check') == '1'
        except Exception:
            redis_ok = False

        celery_ok = None
        try:
            from ecommerce.celery import app as celery_app
            pings = celery_app.control.inspect(timeout=1).ping()
            celery_ok = bool(pings)
        except Exception:
            celery_ok = False

        return {'db': db_ok, 'redis': redis_ok, 'celery': celery_ok}
