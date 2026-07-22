from django.db import migrations

# Regla del modulo Renting: PaymentResult es el unico punto de decision que
# comunica al cliente. Este migration actualiza el copy de 'rental_payment_confirmed'
# (ya sembrada en 0014, ahora referencia el Order oficial en vez de solo el
# ticket de operacion) y siembra por primera vez 'rental_payment_failed'
# (referenciada por RentalRequestCommands.release_on_payment_failure desde
# siempre, pero sin plantilla real hasta ahora -- ver ARQUITECTURA_COMPLETA_RENTIG.md).
TEMPLATES = [
    {
        'slug': 'rental_payment_confirmed',
        'name': 'Alquiler confirmado (pago en linea)',
        'ws_event_type': 'rental_payment_confirmed',
        'subject': 'Hemos recibido correctamente tu pago',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Tu pago fue aprobado exitosamente.\n\n'
            'Numero de pedido:\n'
            '{{order_uuid}}\n\n'
            'Estado:\n\n'
            'Pago aprobado\n\n'
            'En este momento nuestro equipo comenzara el proceso de programacion '
            'y preparacion de la entrega.\n\n'
            'Puedes consultar el estado desde:\n\n'
            'Mi Cuenta -> Mis Pedidos'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'rental_payment_failed',
        'name': 'Pago de alquiler rechazado/fallido',
        'ws_event_type': 'rental_payment_failed',
        'subject': 'Tu pago fue rechazado',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Lamentablemente el pago de tu solicitud de alquiler fue rechazado.\n\n'
            'No se genero ningun pedido.\n\n'
            'Puedes intentar nuevamente utilizando otro medio de pago.'
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
    # No revierte 'rental_payment_confirmed' a su copy anterior (0014 sigue
    # siendo su seed original si se hace rollback total); solo retira la
    # plantilla nueva que esta migracion introduce.
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.filter(slug='rental_payment_failed').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('renting', '0024_equipmentvariant_is_active_db_index'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
