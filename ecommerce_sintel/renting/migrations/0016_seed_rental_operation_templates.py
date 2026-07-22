from django.db import migrations


TEMPLATES = [
    {
        'slug': 'rental_dispatch_assigned',
        'name': 'Operacion de renting asignada al transportista',
        'ws_event_type': 'rental_dispatch_assigned',
        'subject': 'Nueva entrega de renting asignada - {{equipment_name}}',
        'email_body': (
            'Se te asigno la solicitud {{request_uuid}}.\n\n'
            'Equipo: {{equipment_name}}\nDireccion: {{address}}\n'
            'Entrega: {{delivery_date}} {{delivery_time}}\n'
            'Recogida: {{pickup_date}} {{pickup_time}}\nVehiculo: {{vehicle}}\n'
            'Instrucciones: {{instructions}}\n'
            'Seguimiento: /panel/ordenes/renting'
        ),
        'whatsapp_template_name': '', 'is_active': True,
    },
    {
        'slug': 'rental_delivery_scheduled',
        'name': 'Entrega de renting programada para cliente',
        'ws_event_type': 'rental_delivery_scheduled',
        'subject': 'Entrega de tu alquiler programada - {{equipment_name}}',
        'email_body': (
            'Tu entrega fue programada oficialmente.\n\nEquipo: {{equipment_name}}\n'
            'Direccion: {{address}}\nEntrega: {{delivery_date}} {{delivery_time}}\n'
            'Recogida: {{pickup_date}} {{pickup_time}}\n'
            'Transportista: {{dispatcher_name}}\nVehiculo: {{vehicle}}\n'
            'Instrucciones: {{instructions}}'
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
        ('renting', '0015_rentaloperation_rentaloperationevent_and_more'),
        ('notifications', '0001_initial'),
    ]
    operations = [migrations.RunPython(seed, reverse_code=reverse)]
