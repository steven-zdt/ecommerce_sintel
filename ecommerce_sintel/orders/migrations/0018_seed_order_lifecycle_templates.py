from django.db import migrations

# Auditoria de Email en produccion (PLAN_AUDITORIA_EMAIL_PRODUCCION_SINTEL_LOOP.md, Fase 0,
# 2026-09-23): 'order_created' (OrderCommands.create_from_cart(), orders/services/commands.py) y
# 'order_paid' (payment/shared/commands.py::confirm_payment(), disparado justo despues de
# FulfillmentCommands.ensure_shipment_for_order()) llevan referenciados en codigo real desde antes
# de julio 2026 pero NUNCA tuvieron su propia plantilla sembrada -- cada evento fallaba
# silenciosamente (NotificationLog.status=FAILED, 'Plantilla no encontrada o inactiva'),
# confirmado con evidencia real tanto en desarrollo como en produccion (2 y 5 fallos reales
# respectivamente, ultimo el 2026-07-29, coincide con las unicas 6 ordenes reales creadas en
# produccion hasta la fecha de esta auditoria).
#
# Nota de diseno: 'order_paid' NO es redundante con 'shop_order_received' (orders/migrations/
# 0014) aunque ambos puedan dispararse en el mismo commit para una orden con productos fisicos --
# 'shop_order_received' es la actualizacion de estado de FULFILLMENT ("tu pedido entro a
# preparacion"), 'order_paid' es el RECIBO de pago ("confirmamos tu pago"). Para ordenes
# puramente de servicio (sin ProductVariant), ensure_shipment_for_order() nunca crea un Shipment
# -- 'order_paid' es ahi la UNICA confirmacion de pago que el cliente recibe, no un duplicado.
TEMPLATES = [
    {
        'slug': 'order_created',
        'name': 'Pedido recibido (creado desde el carrito)',
        'ws_event_type': 'order_created',
        'subject': 'Recibimos tu pedido - Orden {{order_uuid}}',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Recibimos tu pedido correctamente.\n\n'
            'Numero de pedido:\n'
            '{{order_uuid}}\n\n'
            'Total:\n'
            '${{total}}\n\n'
            'En cuanto confirmemos tu pago comenzaremos a prepararlo.\n\n'
            'Puedes consultar el estado desde:\n\n'
            'Mi Cuenta -> Mis Pedidos\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'order_paid',
        'name': 'Pago de pedido confirmado (recibo)',
        'ws_event_type': 'order_paid',
        'subject': 'Confirmamos tu pago - Pedido {{order_uuid}}',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Confirmamos que tu pago fue aprobado exitosamente.\n\n'
            'Numero de pedido:\n'
            '{{order_uuid}}\n\n'
            'Total pagado:\n'
            '${{total}}\n\n'
            'Este correo es tu recibo de pago. Si tu pedido incluye productos fisicos, '
            'recibiras notificaciones adicionales sobre su preparacion y envio.\n\n'
            'Puedes consultar el estado desde:\n\n'
            'Mi Cuenta -> Mis Pedidos\n\n'
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
        ('orders', '0017_alter_order_payment_method'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
