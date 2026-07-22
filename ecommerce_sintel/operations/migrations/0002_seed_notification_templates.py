from django.db import migrations

TEMPLATES = [
    {
        'slug': 'operation_created',
        'name': 'Operacion creada',
        'ws_event_type': 'operation_created',
        'subject': 'Tu solicitud fue registrada - {{ticket_number}}',
        'email_body': 'Hola, tu solicitud de operacion {{ticket_number}} ha sido registrada exitosamente.',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_assigned',
        'name': 'Recurso asignado',
        'ws_event_type': 'operation_assigned',
        'subject': 'Recurso asignado - {{ticket_number}}',
        'email_body': 'Tu solicitud {{ticket_number}} tiene un recurso asignado: {{assignee_name}} ({{role}}).',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_scheduled',
        'name': 'Visita programada',
        'ws_event_type': 'operation_scheduled',
        'subject': 'Visita programada para el {{scheduled_date}} - {{ticket_number}}',
        'email_body': 'Tu visita ha sido programada para el {{scheduled_date}}.',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_en_route',
        'name': 'Operario en camino',
        'ws_event_type': 'operation_en_route',
        'subject': 'Tu operario esta en camino - {{ticket_number}}',
        'email_body': 'El operario asignado a tu solicitud {{ticket_number}} ya esta en camino.',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_in_progress',
        'name': 'Operacion en progreso',
        'ws_event_type': 'operation_in_progress',
        'subject': 'Operacion iniciada - {{ticket_number}}',
        'email_body': 'Tu solicitud {{ticket_number}} esta siendo atendida en este momento.',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_completed',
        'name': 'Operacion completada',
        'ws_event_type': 'operation_completed',
        'subject': 'Tu solicitud ha sido completada - {{ticket_number}}',
        'email_body': 'Tu solicitud {{ticket_number}} fue completada. Puedes calificar tu experiencia.',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_cancelled',
        'name': 'Operacion cancelada',
        'ws_event_type': 'operation_cancelled',
        'subject': 'Tu solicitud fue cancelada - {{ticket_number}}',
        'email_body': 'Tu solicitud {{ticket_number}} fue cancelada.',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'operation_review_received',
        'name': 'Resena recibida',
        'ws_event_type': 'operation_review_received',
        'subject': 'Gracias por tu calificacion - {{ticket_number}}',
        'email_body': 'Recibimos tu calificacion de {{rating}} estrellas para la solicitud {{ticket_number}}.',
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
    NotificationTemplate.objects.filter(
        slug__in=[t['slug'] for t in TEMPLATES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0001_initial'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_code=reverse_templates),
    ]
