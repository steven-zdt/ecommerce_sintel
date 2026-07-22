from django.db import migrations

TEMPLATES = [
    {
        'slug': 'admin_password_reset',
        'name': 'Restablecimiento de contraseña por administrador',
        'ws_event_type': '',
        'subject': 'Tu contraseña ha sido restablecida - Sintel',
        'email_body': (
            'Hola,\n\n'
            'Un administrador ha restablecido tu contraseña.\n\n'
            'Tu nueva contraseña temporal es: {{ temp_password }}\n\n'
            'Te recomendamos iniciar sesión y cambiarla lo antes posible.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'admin_email_verification',
        'name': 'Reenvio de verificacion de correo',
        'ws_event_type': '',
        'subject': 'Verifica tu correo - Sintel',
        'email_body': (
            'Hola,\n\n'
            'Haz clic en el siguiente enlace para verificar tu correo:\n\n'
            '{{ verification_link }}\n\n'
            'Este enlace expira en 24 horas.\n\n'
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
    NotificationTemplate.objects.filter(
        slug__in=[t['slug'] for t in TEMPLATES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_delete_vendorprofile'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_code=reverse_templates),
    ]
