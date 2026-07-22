"""
Automatiza la auditoria manual de bypasses al patron
NotificationCommands.dispatch_notification() (ver security/.AGENT/docs y
notifications/CLAUDE.md). Es un reporte, no un gate de CI -- no falla el
comando ni el build si encuentra hallazgos.
"""
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.models import NotificationTemplate, NotificationLog

# Directorios que nunca se escanean: no son codigo de apps de negocio, o son
# subsistemas paralelos ya documentados (marketing tiene su propio motor
# multicanal de campanias masivas, separado a proposito del flujo
# transaccional -- ver marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md).
EXCLUDED_DIRS = {
    'notifications', 'marketing', 'migrations', '__pycache__', 'node_modules',
    'frontend', 'venv', '.venv', 'static', 'media', 'ai_engine', 'ai_skills',
    '.git', 'scratchpad',
}

# Bypasses ya conocidos y aceptados (contenido dinamico/sensible que no encaja
# bien en NotificationTemplate, o infraestructura de bajo nivel que el propio
# patron sancionado usa por debajo) -- documentados explicitamente en vez de
# reportarlos cada vez como hallazgo nuevo.
ALLOWLIST = {
    os.path.normpath('quotes/tasks.py'): 'Adjunta un PDF generado dinamicamente a la cotizacion.',
    os.path.normpath('users/services/commands.py'): 'Codigo OTP de verificacion de registro (dato sensible, un solo uso).',
    os.path.normpath('ecommerce/ws_notify.py'): 'Helper de bajo nivel que notifications/tasks.py ya envuelve -- no es un bypass, es el primitivo del patron sancionado.',
    os.path.normpath('support/consumers.py'): 'Entrega en tiempo real del mensaje de chat (el contenido mismo de la conversacion, no un aviso sobre otro evento) -- caso legitimo separado, no una notificacion.',
}

BYPASS_PATTERNS = [
    re.compile(r'\bsend_mail\s*\('),
    re.compile(r'\bEmailMessage\s*\('),
    re.compile(r'\bEmailMultiAlternatives\s*\('),
    # Solo el ENVIO (group_send) es un bypass real -- group_add/group_discard
    # son boilerplate legitimo de cualquier Channels consumer al conectar/desconectar.
    re.compile(r'channel_layer\s*\.\s*group_send'),
    re.compile(r'\bWhatsAppClient\s*\('),
]


class Command(BaseCommand):
    help = 'Audita bypasses al patron dispatch_notification, plantillas inactivas y slugs invalidos.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Auditoria de Notifications ==='))
        self._scan_bypasses()
        self._report_inactive_templates()
        self._report_invalid_slugs()

    def _scan_bypasses(self):
        self.stdout.write('\n-- Bypasses de comunicacion directa --')
        found_any = False
        for root, dirs, files in os.walk(settings.BASE_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.normpath(os.path.relpath(full_path, settings.BASE_DIR))
                if rel_path in ALLOWLIST:
                    continue
                try:
                    with open(full_path, encoding='utf-8') as fh:
                        content = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                for pattern in BYPASS_PATTERNS:
                    if pattern.search(content):
                        found_any = True
                        self.stdout.write(self.style.WARNING(
                            f'  [BYPASS] {rel_path} -- coincide con "{pattern.pattern}"'
                        ))
        if not found_any:
            self.stdout.write(self.style.SUCCESS('  Sin bypasses nuevos detectados.'))

        if ALLOWLIST:
            self.stdout.write('\n-- Bypasses conocidos, aceptados (allowlist) --')
            for path, reason in ALLOWLIST.items():
                self.stdout.write(f'  [OK] {path} -- {reason}')

    def _report_inactive_templates(self):
        self.stdout.write('\n-- Plantillas inactivas --')
        inactive = NotificationTemplate.objects.filter(is_active=False).values_list('slug', flat=True)
        if not inactive:
            self.stdout.write(self.style.SUCCESS('  Ninguna.'))
            return
        for slug in inactive:
            self.stdout.write(self.style.WARNING(f'  [INACTIVA] {slug}'))

    def _report_invalid_slugs(self):
        self.stdout.write('\n-- Slugs invalidos referenciados en dispatch_notification (ultimos eventos) --')
        broken = (
            NotificationLog.objects
            .filter(template__isnull=True)
            .exclude(template_slug='')
            .values_list('template_slug', flat=True)
        )
        if not broken:
            self.stdout.write(self.style.SUCCESS('  Ninguno.'))
            return
        counts = {}
        for slug in broken:
            counts[slug] = counts.get(slug, 0) + 1
        for slug, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            self.stdout.write(self.style.ERROR(f'  [ROTO] {slug} -- {count} intento(s)'))
