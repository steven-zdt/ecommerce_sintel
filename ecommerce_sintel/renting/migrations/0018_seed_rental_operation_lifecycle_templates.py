from django.db import migrations


TEMPLATES = [
    {
        'slug': 'rental_operation_created',
        'name': 'Solicitud de renting ingreso a Operaciones',
        'ws_event_type': 'rental_operation_created',
        'subject': 'Tu alquiler entro a programacion - {{equipment_name}}',
        'email_body': (
            'Tu solicitud {{request_uuid}} fue aprobada y ahora esta en manos del '
            'equipo de Operaciones.\n\nEquipo: {{equipment_name}}\n'
            'Te avisaremos en cuanto se programe la entrega.'
        ),
        'whatsapp_template_name': '', 'is_active': True,
    },
    {
        'slug': 'rental_equipment_delivered',
        'name': 'Equipo de renting entregado al cliente',
        'ws_event_type': 'rental_equipment_delivered',
        'subject': 'Tu equipo fue entregado - {{equipment_name}}',
        'email_body': (
            'Confirmamos la entrega de tu alquiler.\n\nEquipo: {{equipment_name}}\n'
            'Direccion: {{address}}\nFecha de entrega: {{delivery_date}}\n'
            'La fecha de recogida programada es: {{pickup_date}}.'
        ),
        'whatsapp_template_name': '', 'is_active': True,
    },
    {
        'slug': 'rental_pickup_scheduled',
        'name': 'Recogida de renting proxima',
        'ws_event_type': 'rental_pickup_scheduled',
        'subject': 'Tu equipo esta listo para ser recogido - {{equipment_name}}',
        'email_body': (
            'Tu equipo entra en proceso de recogida.\n\nEquipo: {{equipment_name}}\n'
            'Direccion: {{address}}\nFecha de recogida: {{pickup_date}}.'
        ),
        'whatsapp_template_name': '', 'is_active': True,
    },
    {
        'slug': 'rental_completed',
        'name': 'Operacion de renting finalizada',
        'ws_event_type': 'rental_completed',
        'subject': 'Tu alquiler fue finalizado - {{equipment_name}}',
        'email_body': (
            'Tu operacion de alquiler quedo completada.\n\nEquipo: {{equipment_name}}\n'
            'Gracias por confiar en nosotros.'
        ),
        'whatsapp_template_name': '', 'is_active': True,
    },
]


def seed(apps, schema_editor):
    model = apps.get_model('notifications', 'NotificationTemplate')
    for data in TEMPLATES:
        model.objects.update_or_create(
            slug=data['slug'], defaults={k: v for k, v in data.items() if k != 'slug'}
        )


def reverse(apps, schema_editor):
    apps.get_model('notifications', 'NotificationTemplate').objects.filter(
        slug__in=[item['slug'] for item in TEMPLATES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('renting', '0017_rental_operation_incidents'),
        ('notifications', '0001_initial'),
    ]
    operations = [migrations.RunPython(seed, reverse_code=reverse)]
