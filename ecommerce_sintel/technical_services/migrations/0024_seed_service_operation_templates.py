from django.db import migrations

TEMPLATES = [
    {
        'slug': 'service_operation_created',
        'name': 'Operacion de servicio creada (recepcion)',
        'ws_event_type': 'service_operation_created',
        'subject': 'Tu servicio entro a programacion - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu pago fue aprobado y tu solicitud de servicio ({{service}}) entro al equipo '
            'de Operaciones para ser planeada.\n\n'
            'Orden: {{order_uuid}}\n\n'
            'Te avisaremos en cuanto tengamos la fecha y el profesional asignado.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'service_operation_assigned',
        'name': 'Tecnico asignado a una operacion de servicio',
        'ws_event_type': 'service_operation_assigned',
        'subject': 'Nueva visita asignada - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Se te asigno una visita tecnica.\n\n'
            'Orden: {{order_uuid}}\n'
            'Fecha: {{scheduled_date}}\n'
            'Hora: {{scheduled_time}}\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'service_visit_scheduled',
        'name': 'Visita de servicio programada (cliente notificado)',
        'ws_event_type': 'service_visit_scheduled',
        'subject': 'Tu visita tecnica fue programada - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu servicio tecnico quedo programado.\n\n'
            'Profesional asignado: {{technician_name}}\n'
            'Fecha: {{scheduled_date}}\n'
            'Hora: {{scheduled_time}}\n'
            'Direccion: {{address}}\n\n'
            'NUMERO DE ORDEN: {{order_uuid}}\n\n'
            'Puedes ver el seguimiento de tu servicio desde Mi Cuenta > Pedidos.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'service_operation_cancelled',
        'name': 'Operacion de servicio cancelada',
        'ws_event_type': 'service_operation_cancelled',
        'subject': 'Tu servicio fue cancelado - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu servicio tecnico (orden {{order_uuid}}) fue cancelado.\n\n'
            'Motivo: {{reason}}\n\n'
            'Si tienes dudas, contacta a nuestro equipo de soporte.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'service_incident_reported',
        'name': 'Incidencia reportada en operacion de servicio',
        'ws_event_type': 'service_incident_reported',
        'subject': 'Incidencia reportada - Orden {{order_uuid}}',
        'email_body': (
            'Se reporto una incidencia en la orden {{order_uuid}}.\n\n'
            'Notas: {{notes}}'
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
        ('technical_services', '0023_serviceoperation_serviceoperationevent_and_more'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
