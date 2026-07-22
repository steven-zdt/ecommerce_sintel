from django.db import migrations

# Fase 11 AI Core (Proactividad, cierre): plantilla para el cross-sell minimo
# de clientes recurrentes (3+ Order pagadas) via el Event Bus (Componente 8).
SLUG = 'cliente_recurrente_cross_sell'


def seed_template(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.update_or_create(
        slug=SLUG,
        defaults={
            'name': 'Cliente recurrente - venta cruzada',
            'subject': 'Tenemos algo especial para vos',
            'email_body': (
                'Hola, gracias por confiar en Sintel {{ orders_count }} veces. '
                'Tenemos ofertas y novedades pensadas para clientes como vos -- '
                'escribenos si queres conocerlas.'
            ),
            'ws_event_type': 'FREQUENT_CUSTOMER_OFFER',
            'whatsapp_template_name': '',
            'is_active': True,
        },
    )


def remove_template(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_seed_proactive_templates'),
    ]

    operations = [migrations.RunPython(seed_template, reverse_code=remove_template)]
