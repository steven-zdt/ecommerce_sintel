from django.db import migrations

# Fase 14 (AUDITORIA/28_AUDITORIA_OPERATIONS.md, 2026-08-03): plantilla para
# operations.tasks.notify_stale_operation_tickets -- notifica al tecnico/despachador ACTIVO
# asignado, no al cliente (a diferencia de las 8 plantillas de 0002, todas client-facing).
TEMPLATE = {
    'slug': 'operacion_estancada',
    'name': 'Operacion estancada',
    'subject': 'Ticket {{ ticket_number }} sin avance',
    'email_body': (
        'El ticket de operacion {{ ticket_number }} lleva mas de 48 horas sin ningun avance '
        'desde tu ultima asignacion. Revisa el estado y actualiza el ticket en el panel.'
    ),
    'ws_event_type': 'OPERATION_TICKET_STALE',
    'whatsapp_template_name': '',
    'is_active': True,
}


def seed_template(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.update_or_create(
        slug=TEMPLATE['slug'],
        defaults={k: v for k, v in TEMPLATE.items() if k != 'slug'},
    )


def remove_template(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.filter(slug=TEMPLATE['slug']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0005_operationassignment_status_db_index'),
        ('notifications', '0006_add_sms_channel'),
    ]

    operations = [migrations.RunPython(seed_template, reverse_code=remove_template)]
