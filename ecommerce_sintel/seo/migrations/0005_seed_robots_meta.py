"""
Siembra la metaetiqueta 'robots' por defecto (index, follow) sitewide --
parte de las correcciones SEO recomendadas (auditoria externa). Se modela
como un SiteMetaTag mas (no un campo nuevo en ningun otro lado): es
exactamente el caso de uso para el que existe ese modelo -- un <meta>
simple, administrable, sin datos institucionales involucrados.
"""
from django.db import migrations


def seed_robots_meta(apps, schema_editor):
    SiteMetaTag = apps.get_model('seo', 'SiteMetaTag')
    SiteMetaTag.objects.get_or_create(
        provider='custom',
        meta_name='robots',
        defaults=dict(
            name='Robots (directiva de indexacion)',
            tag_type='seo',
            description='Directiva por defecto para crawlers de buscadores en todo el sitio.',
            meta_content='index, follow',
            priority=0,
            is_active=True,
            environment='all',
        ),
    )


def remove_robots_meta(apps, schema_editor):
    SiteMetaTag = apps.get_model('seo', 'SiteMetaTag')
    SiteMetaTag.objects.filter(provider='custom', meta_name='robots').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0004_seed_meta_verification_file'),
    ]

    operations = [
        migrations.RunPython(seed_robots_meta, remove_robots_meta),
    ]
