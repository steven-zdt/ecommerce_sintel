from django.db import migrations

TEMPLATES = [
    {
        'slug': 'kyc_registered_pending',
        'name': 'Registro creado, pendiente de verificacion KYC',
        'ws_event_type': 'kyc_registered_pending',
        'subject': 'Bienvenido a Sintel - Tu cuenta esta pendiente de validacion',
        'email_body': (
            'Hola,\n\n'
            'Tu cuenta ha sido creada exitosamente en Sintel.\n\n'
            'Antes de poder operar (comprar, vender u ofrecer servicios) nuestro '
            'equipo debe validar tu identidad. Ingresa a la plataforma para cargar '
            'los documentos requeridos.\n\n'
            'Te avisaremos por correo cuando finalice la revision.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'kyc_submitted_for_review',
        'name': 'KYC enviado a revision',
        'ws_event_type': 'kyc_submitted_for_review',
        'subject': '',
        'email_body': '',
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'kyc_approved',
        'name': 'Verificacion KYC aprobada',
        'ws_event_type': 'kyc_approved',
        'subject': 'Tu cuenta Sintel fue aprobada',
        'email_body': (
            'Hola,\n\n'
            'Tu verificacion de identidad fue aprobada. Ya puedes comprar, vender '
            'y ofrecer tus servicios en Sintel.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'kyc_rejected',
        'name': 'Verificacion KYC rechazada',
        'ws_event_type': 'kyc_rejected',
        'subject': 'Tu verificacion de identidad Sintel fue rechazada',
        'email_body': (
            'Hola,\n\n'
            'Tu verificacion de identidad fue rechazada.\n\n'
            'Motivo: {{ reason }}\n\n'
            'Ingresa a la plataforma para corregir tus datos/documentos y volver a enviarlos.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'kyc_info_requested',
        'name': 'Informacion adicional solicitada (KYC)',
        'ws_event_type': 'kyc_info_requested',
        'subject': 'Necesitamos informacion adicional para validar tu cuenta',
        'email_body': (
            'Hola,\n\n'
            'Nuestro equipo necesita informacion adicional para continuar tu '
            'verificacion de identidad.\n\n'
            'Mensaje: {{ message }}\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'kyc_blocked',
        'name': 'Cuenta bloqueada (KYC)',
        'ws_event_type': 'kyc_blocked',
        'subject': 'Tu cuenta Sintel ha sido bloqueada',
        'email_body': (
            'Hola,\n\n'
            'Tu cuenta ha sido bloqueada por nuestro equipo.\n\n'
            'Motivo: {{ reason }}\n\n'
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
        ('kyc', '0001_initial'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_code=reverse_templates),
    ]
