from django.db import migrations

TEMPLATES = [
    {
        'slug': 'rental_payment_confirmed',
        'name': 'Alquiler confirmado (pago en linea)',
        'ws_event_type': 'rental_payment_confirmed',
        'subject': 'Tu alquiler fue confirmado - Ticket {{ticket_number}}',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu pago fue aprobado y tu solicitud de alquiler para {{equipment_name}} '
            'quedo confirmada.\n\n'
            'Detalle de tu reserva:\n'
            '- Periodo: {{start_date}} al {{end_date}}\n'
            '- Total pagado: ${{grand_total}} COP\n\n'
            'NUMERO DE TICKET DE SERVICIO: {{ticket_number}}\n\n'
            'Usa este numero de ticket para dar seguimiento a la entrega de tu equipo '
            'desde Mi Cuenta > Operaciones.\n\n'
            'Gracias por confiar en Sintel.'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'rental_cod_confirmed',
        'name': 'Alquiler confirmado (contra entrega, aprobado por admin)',
        'ws_event_type': 'rental_cod_confirmed',
        'subject': 'Tu alquiler fue confirmado - Ticket {{ticket_number}}',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu solicitud de alquiler para {{equipment_name}} fue aprobada y quedo '
            'confirmada. El pago se realiza contra entrega.\n\n'
            'Detalle de tu reserva:\n'
            '- Periodo: {{start_date}} al {{end_date}}\n'
            '- Total a pagar: ${{grand_total}} COP\n\n'
            'NUMERO DE TICKET DE SERVICIO: {{ticket_number}}\n\n'
            'Usa este numero de ticket para dar seguimiento a la entrega de tu equipo '
            'desde Mi Cuenta > Operaciones.\n\n'
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
        ('renting', '0013_rental_lifecycle_v2'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
