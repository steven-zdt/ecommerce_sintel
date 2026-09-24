"""HARDENING F7/C4 (2026-09-24): derecho al olvido a demanda (Habeas Data). Borra FISICAMENTE toda la memoria del asistente de un cliente.
Uso: python manage.py forget_customer_memory --email cliente@dominio.com"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from customer_memory.services.commands import CustomerMemoryCommands


class Command(BaseCommand):
    help = 'Borra toda la memoria del asistente de un cliente (por correo).'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)

    def handle(self, *args, **opts):
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=opts['email'].strip())
        except User.DoesNotExist:
            raise CommandError('No existe un usuario con ese correo.')
        n = CustomerMemoryCommands.forget_all(user)
        self.stdout.write(f'recuerdos borrados: {n}')
