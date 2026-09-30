from django.db import migrations

# Auditoria de Email en produccion (PLAN_AUDITORIA_EMAIL_PRODUCCION_SINTEL_LOOP.md, Fase 0,
# 2026-09-23): estos 3 slugs se referencian en renting/services/commands.py desde antes de julio
# 2026 pero nunca tuvieron plantilla sembrada -- fallaban silenciosamente (NotificationLog.
# status=FAILED, 'Plantilla no encontrada o inactiva'), confirmado con evidencia real en
# produccion (3 fallos reales de 'rental_cod_review_pending', ultimo 2026-08-01).
#
# Nota real encontrada durante esta auditoria (documentada, NO corregida aqui -- corregirla
# cambiaria el enrutamiento de destinatario, fuera del alcance minimo de "la plantilla no
# existe"): tanto 'rental_payment_conflict_customer' como 'rental_payment_conflict_admin' se
# disparan con `dispatch_notification(user=rental_request.user, ...)` -- el MISMO usuario cliente
# en ambas llamadas, solo el `ws_group` cambia ('user_{uuid}' vs 'admin_notifications'). El canal
# WebSocket si distingue destinatario (por grupo), pero el canal Email de AMBAS plantillas termina
# llegando hoy a la bandeja del CLIENTE, no de un admin real -- ver EMAIL_GAPS.md. Por eso el
# copy de '..._admin' se redacta aqui en un tono seguro para que lo reciba el cliente (sin
# instrucciones internas), no como si fuera un admin real quien lo lee.
TEMPLATES = [
    {
        'slug': 'rental_cod_review_pending',
        'name': 'Solicitud de alquiler COD en revision',
        'ws_event_type': 'rental_cod_review_pending',
        'subject': 'Tu solicitud de alquiler esta en revision',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Recibimos tu solicitud de alquiler con pago contra entrega (COD).\n\n'
            'Equipo:\n'
            '{{equipment_name}}\n\n'
            'Total:\n'
            '${{grand_total}}\n\n'
            'Solicitud:\n'
            '{{request_uuid}}\n\n'
            'Tu solicitud quedo pendiente de revision y aprobacion por nuestro equipo. '
            'Te avisaremos apenas se confirme.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'rental_payment_conflict_customer',
        'name': 'Conflicto de pago en solicitud de alquiler (cliente)',
        'ws_event_type': 'rental_payment_conflict_customer',
        'subject': 'Hubo un problema con el pago de tu solicitud de alquiler',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Detectamos un inconveniente al procesar el pago de tu solicitud de alquiler.\n\n'
            'Equipo:\n'
            '{{equipment_name}}\n\n'
            'Total:\n'
            '${{grand_total}}\n\n'
            'Solicitud:\n'
            '{{request_uuid}}\n\n'
            'Tu equipo aun NO fue reservado. Nuestro equipo revisara el caso y se pondra en '
            'contacto contigo. Si tienes dudas, puedes escribirnos indicando el numero de '
            'solicitud.\n\n'
            'Equipo Sintel'
        ),
        'whatsapp_template_name': '',
        'is_active': True,
    },
    {
        'slug': 'rental_payment_conflict_admin',
        'name': 'Conflicto de pago en solicitud de alquiler (seguimiento)',
        'ws_event_type': 'rental_payment_conflict_admin',
        'subject': 'Seguimiento: conflicto de pago en tu solicitud de alquiler',
        'email_body': (
            'Hola {{user_name}},\n\n'
            'Este es un mensaje de seguimiento sobre el conflicto de pago detectado en tu '
            'solicitud de alquiler.\n\n'
            'Equipo:\n'
            '{{equipment_name}}\n\n'
            'Total:\n'
            '${{grand_total}}\n\n'
            'Solicitud:\n'
            '{{request_uuid}}\n\n'
            'Nuestro equipo ya fue notificado internamente y esta revisando el caso. Te '
            'contactaremos con una resolucion a la brevedad.\n\n'
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
        ('renting', '0037_alter_rentalrequestpaymentinfo_payment_status'),
        ('notifications', '0001_initial'),
    ]

    operations = [migrations.RunPython(seed_templates, reverse_code=reverse_templates)]
