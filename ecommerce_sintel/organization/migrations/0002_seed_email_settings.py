from django.db import migrations


def seed_email_settings(apps, schema_editor):
    """
    Siembra un EmailSettings con los valores reales actuales de settings
    (snapshot unico -- de aqui en adelante organization es la fuente de
    verdad, futuros cambios se hacen desde el panel admin, no editando .env).
    admin_login_url queda vacio a proposito: FRONTEND_ADMIN_LOGIN_URL nunca
    se configuro en ningun .env del proyecto (bug fantasma encontrado en la
    auditoria Fase 1, ver MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md).
    """
    EmailSettings = apps.get_model('organization', 'EmailSettings')
    from django.conf import settings

    if not EmailSettings.objects.exists():
        EmailSettings.objects.create(
            default_from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            frontend_base_url=getattr(settings, 'FRONTEND_BASE_URL', ''),
            admin_login_url='',
            is_active=True,
        )


def unseed_email_settings(apps, schema_editor):
    EmailSettings = apps.get_model('organization', 'EmailSettings')
    EmailSettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_email_settings, unseed_email_settings),
    ]
