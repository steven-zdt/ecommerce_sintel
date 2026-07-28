from django.db import migrations

TEMPLATES = [
    {
        'slug': 'rental_comodato_review_pending',
        'name': 'Solicitud de comodato en revision (admin)',
        'ws_event_type': 'rental_comodato_review_pending',
        'subject': 'Nueva solicitud de comodato pendiente de revision',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu solicitud de comodato para {{equipment_name}} fue recibida y esta '
            'en revision. Un asesor la evaluara y te notificaremos la decision.\n\n'
            'No se realiza ningun cobro por este contrato.\n\n'
            'Gracias por confiar en Sintel.'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'rental_comodato_confirmed',
        'name': 'Comodato aprobado (admin)',
        'ws_event_type': 'rental_comodato_confirmed',
        'subject': 'Tu comodato fue aprobado - Ticket {{ticket_number}}',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu solicitud de comodato para {{equipment_name}} fue aprobada y quedo '
            'confirmada. Este contrato no requiere pago.\n\n'
            'Detalle de tu reserva:\n'
            '- Periodo: {{start_date}} al {{end_date}}\n\n'
            'NUMERO DE TICKET DE SERVICIO: {{ticket_number}}\n\n'
            'Usa este numero de ticket para dar seguimiento a la entrega de tu equipo '
            'desde Mi Cuenta > Operaciones.\n\n'
            'Gracias por confiar en Sintel.'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'rental_comodato_rejected',
        'name': 'Comodato rechazado (admin)',
        'ws_event_type': 'rental_comodato_rejected',
        'subject': 'Tu solicitud de comodato no fue aprobada',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu solicitud de comodato para {{equipment_name}} no fue aprobada.\n\n'
            '{{reason}}\n\n'
            'Si tienes preguntas, contactanos.\n\n'
            'Gracias por tu interes en Sintel.'
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
        ('renting', '0030_rentalperiod_commercial_type_and_more'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
