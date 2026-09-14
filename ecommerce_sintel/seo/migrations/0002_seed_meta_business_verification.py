"""
Siembra el primer SiteMetaTag: verificacion de dominio de Meta Business
Suite. El codigo de verificacion vive UNICAMENTE en esta migracion de datos
(base de datos) -- nunca en un template ni en settings. Editable/eliminable
libremente por un admin desde /panel/seo/meta-tags despues de aplicada.

get_or_create evita duplicar la fila si la migracion corre mas de una vez
sobre la misma BD (idempotente).
"""
from django.db import migrations


def seed_meta_business_verification(apps, schema_editor):
    SiteMetaTag = apps.get_model('seo', 'SiteMetaTag')
    SiteMetaTag.objects.get_or_create(
        provider='meta',
        meta_name='facebook-domain-verification',
        defaults=dict(
            name='Meta Business Verification',
            tag_type='domain_verification',
            description=(
                'Verificacion de dominio para Meta Business Suite '
                '(Facebook/Instagram Ads Manager).'
            ),
            meta_content='0c6qg0sg1qsfxhoth3srzf53i62neb',
            priority=0,
            is_active=True,
            environment='all',
        ),
    )


def remove_meta_business_verification(apps, schema_editor):
    SiteMetaTag = apps.get_model('seo', 'SiteMetaTag')
    SiteMetaTag.objects.filter(
        provider='meta',
        meta_name='facebook-domain-verification',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_meta_business_verification, remove_meta_business_verification),
    ]
