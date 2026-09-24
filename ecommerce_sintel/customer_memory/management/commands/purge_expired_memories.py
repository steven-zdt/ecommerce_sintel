"""HARDENING F7/C2 (2026-09-24): borrado fisico de recuerdos expirados (los expirados ya no se devuelven en lecturas).
Programar en Celery Beat en el despliegue (p. ej. diario). Uso: python manage.py purge_expired_memories [--grace-days 30]"""
from django.core.management.base import BaseCommand

from customer_memory.services.commands import CustomerMemoryCommands


class Command(BaseCommand):
    help = 'Borra fisicamente los recuerdos de cliente expirados hace mas de N dias.'

    def add_arguments(self, parser):
        parser.add_argument('--grace-days', type=int, default=30)

    def handle(self, *args, **opts):
        n = CustomerMemoryCommands.purge_expired(grace_days=opts['grace_days'])
        self.stdout.write(f'recuerdos expirados borrados: {n}')
