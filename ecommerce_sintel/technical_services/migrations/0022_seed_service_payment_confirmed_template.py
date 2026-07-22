from django.db import migrations

TEMPLATES = [
    {
        'slug': 'service_payment_confirmed',
        'name': 'Servicio tecnico confirmado (pago aprobado)',
        'ws_event_type': 'service_payment_confirmed',
        'subject': 'Tu servicio fue confirmado - Orden {{order_uuid}}',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu pago fue aprobado y tu solicitud de servicio para {{service}} '
            'quedo confirmada.\n\n'
            'Detalle de tu solicitud:\n'
            '- Profesional asignado: {{technician}}\n'
            '- Fecha programada: {{scheduled_date}}\n'
            '- Total pagado: ${{total}} COP\n\n'
            'NUMERO DE ORDEN: {{order_uuid}}\n\n'
            'Puedes ver el seguimiento de tu servicio desde Mi Cuenta > Pedidos.\n\n'
            'Gracias por confiar en Sintel.'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
]


def seed_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    for data in TEMPLATES:
        NotificationTemplate.objects.update_or_create(
            slug=data['slug'],
            defaults={k: v for k, v in data.items() if k != 'slug'},
        )


def reverse_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.filter(slug__in=[t['slug'] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('technical_services', '0021_remove_serviceconfiguration_technical_s_uuid_1565d1_idx_and_more'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
