from django.db import migrations

# Estos 2 slugs son disparados desde services/commands.py (dispatch_notification
# en request_service() y en ServiceTimelineCommands.add_timeline_event()) desde
# que ambos flujos existen, pero -- a diferencia de service_payment_confirmed
# (migration 0022) y los 5 templates de operaciones (migration 0024) -- nunca
# tuvieron una migracion que los sembrara. Auditoria 2026-07-17: existian en la
# BD de dev solo porque alguien los creo manualmente por el panel admin; en un
# entorno nuevo, ambas notificaciones (admin WS al crear solicitud + cliente al
# cambiar de estado) fallarian en silencio (dispatch_notification no truena,
# solo loguea NotificationLog en FAILED). Valores tomados EXACTAMENTE de los
# que ya existian en dev para que este RunPython sea un no-op ahi.
TEMPLATES = [
    {
        'slug': 'service_request_created',
        'name': 'Solicitud de servicio tecnico creada',
        'ws_event_type': 'NEW_SERVICE_REQUEST',
        'subject': 'Solicitud de servicio recibida - Sintel',
        'email_body': (
            'Hola {{ user_name }},\n\n'
            'Recibimos tu solicitud de servicio: {{ service }}.\n'
            'Orden: {{ order_uuid }}\n\n'
            'Nuestro equipo te contactara pronto.'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'service_status_updated',
        'name': 'Estado de servicio tecnico actualizado',
        'ws_event_type': 'SERVICE_STATUS_UPDATED',
        'subject': 'Actualizacion de tu servicio - Sintel',
        'email_body': (
            'Hola {{ user_name }},\n\n'
            'El estado de tu servicio (orden {{ order_uuid }}) cambio a: {{ status }}.\n'
            '{% if notes %}Notas: {{ notes }}{% endif %}'
        ),
        'whatsapp_template_name': 'service_status_update',
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
        ('technical_services', '0029_servicevariant_is_active_db_index'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
