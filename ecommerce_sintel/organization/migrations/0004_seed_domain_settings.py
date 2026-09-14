from django.db import migrations


def seed_domain_settings(apps, schema_editor):
    """
    Siembra el DomainSettings real del proyecto (mismo criterio que
    0002_seed_email_settings: snapshot unico, de aqui en adelante
    organization es la fuente de verdad). Los 3 subdominios ya existen en
    la infraestructura real (ver nginx-common.conf / nginx.prod.conf, ADR-001
    "aislamiento de dominio del panel"). Sin este seed, seo.templatetags.
    seo_tags cae a request.get_host() para el canonical -- correcto pero
    dependiente del Host header en vez de una fuente administrable.
    """
    DomainSettings = apps.get_model('organization', 'DomainSettings')

    if not DomainSettings.objects.exists():
        DomainSettings.objects.create(
            primary_domain='sintel.net.co',
            admin_panel_domain='panel.sintel.net.co',
            api_domain='api.sintel.net.co',
            is_active=True,
        )


def unseed_domain_settings(apps, schema_editor):
    DomainSettings = apps.get_model('organization', 'DomainSettings')
    DomainSettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0003_communicationevent'),
    ]

    operations = [
        migrations.RunPython(seed_domain_settings, unseed_domain_settings),
    ]
