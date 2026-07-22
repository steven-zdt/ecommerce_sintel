from django.db import migrations

TEMPLATES = [
    {
        'slug': 'shop_order_received',
        'name': 'Pedido recibido en Operaciones (pago confirmado)',
        'ws_event_type': 'shop_order_received',
        'subject': 'Tu pedido fue confirmado - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu pago fue confirmado y tu pedido entro a preparacion.\n\n'
            'Orden: {{order_uuid}}\n\n'
            'Te avisaremos en cada paso hasta que llegue a tus manos.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'shop_preparing_order',
        'name': 'Pedido en preparacion',
        'ws_event_type': 'shop_preparing_order',
        'subject': 'Estamos preparando tu pedido - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu pedido {{order_uuid}} esta siendo alistado en nuestra bodega.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'shop_dispatch_assigned',
        'name': 'Transportista asignado al pedido',
        'ws_event_type': 'shop_dispatch_assigned',
        'subject': 'Un transportista fue asignado a tu pedido - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Se asigno un transportista para la entrega de tu pedido {{order_uuid}}.\n\n'
            'Transportista: {{dispatcher_name}}\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'shop_order_shipped',
        'name': 'Pedido despachado',
        'ws_event_type': 'shop_order_shipped',
        'subject': 'Tu pedido fue despachado - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu pedido {{order_uuid}} ya fue despachado.\n\n'
            'Numero de guia: {{tracking_code}}\n'
            'Transportadora: {{carrier_name}}\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'shop_delivery_scheduled',
        'name': 'Entrega programada / en reparto',
        'ws_event_type': 'shop_delivery_scheduled',
        'subject': 'Tu pedido esta en reparto - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu pedido {{order_uuid}} esta en camino.\n\n'
            'Fecha estimada de entrega: {{estimated_delivery}}\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'shop_order_delivered',
        'name': 'Pedido entregado',
        'ws_event_type': 'shop_order_delivered',
        'subject': 'Tu pedido fue entregado - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Tu pedido {{order_uuid}} fue entregado exitosamente.\n\n'
            'Gracias por comprar en Sintel.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'shop_delivery_confirmed',
        'name': 'Cliente confirmo recepcion del pedido',
        'ws_event_type': 'shop_delivery_confirmed',
        'subject': 'Gracias por confirmar tu pedido - Orden {{order_uuid}}',
        'email_body': (
            'Hola,\n\n'
            'Gracias por confirmar la recepcion de tu pedido {{order_uuid}}.\n\n'
            'Equipo Sintel'
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
        ('orders', '0013_shipment_assigned_dispatcher_and_more'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
