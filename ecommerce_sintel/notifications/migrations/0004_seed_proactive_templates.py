from django.db import migrations

# Fase 11 AI Core (Proactividad): plantillas para los 4 escenarios de negocio
# que activan el Event Bus (Componente 8, notifications/tasks.py::
# ai_proactive_room_message_task) via AI_PROACTIVE_SLUGS. Sin plantilla de
# WhatsApp aprobada en Meta -- ese canal queda deshabilitado para estas 4
# (dispatch_notification ya lo maneja como no-op).
TEMPLATES = [
    {
        'slug': 'cotizacion_sin_respuesta',
        'name': 'Cotizacion sin respuesta',
        'subject': 'Seguimos pendientes de tu cotizacion',
        'email_body': (
            'Hola, notamos que tu cotizacion {{ quotation_uuid }} sigue sin '
            'respuesta. Si tienes preguntas o quieres ajustar algo, '
            'escribenos por el chat de soporte.'
        ),
        'ws_event_type': 'QUOTATION_FOLLOWUP',
    },
    {
        'slug': 'renting_por_vencer',
        'name': 'Renting por vencer',
        'subject': 'Tu alquiler esta por vencer',
        'email_body': (
            'Hola, tu periodo de alquiler {{ rental_period_uuid }} vence el '
            '{{ end_date }}. Si necesitas extenderlo o coordinar la '
            'devolucion, escribenos por el chat de soporte.'
        ),
        'ws_event_type': 'RENTAL_EXPIRING_SOON',
    },
    {
        'slug': 'pago_rechazado_seguimiento',
        'name': 'Pago rechazado - seguimiento',
        'subject': 'Tuvimos un problema con tu pago',
        'email_body': (
            'Hola, tu pago (transaccion {{ transaction_uuid }}) fue '
            'rechazado por la pasarela. Podemos ayudarte a intentarlo de '
            'nuevo -- escribenos por el chat de soporte.'
        ),
        'ws_event_type': 'PAYMENT_DECLINED_FOLLOWUP',
    },
    {
        'slug': 'ticket_soporte_sin_seguimiento',
        'name': 'Ticket de soporte sin seguimiento',
        'subject': 'Seguimos con tu caso de soporte',
        'email_body': (
            'Hola, tu conversacion de soporte {{ room_uuid }} quedo en '
            'espera de un agente humano. Seguimos con tu caso -- si '
            'necesitas agregar algo, escribenos por el mismo chat.'
        ),
        'ws_event_type': 'SUPPORT_TICKET_STALE',
    },
]


def seed_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    for tpl in TEMPLATES:
        NotificationTemplate.objects.update_or_create(
            slug=tpl['slug'],
            defaults={
                'name': tpl['name'],
                'subject': tpl['subject'],
                'email_body': tpl['email_body'],
                'ws_event_type': tpl['ws_event_type'],
                'whatsapp_template_name': '',
                'is_active': True,
            },
        )


def remove_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.filter(
        slug__in=[tpl['slug'] for tpl in TEMPLATES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_backfill_template_slug'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=remove_templates)]
