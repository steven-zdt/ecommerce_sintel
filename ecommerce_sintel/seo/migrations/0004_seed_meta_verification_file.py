"""
Siembra el archivo de verificacion de Meta Business Suite (metodo "Subir
archivo HTML", alternativo al de metaetiqueta ya sembrado en 0002). El
contenido vive UNICAMENTE en esta migracion de datos -- nunca en un archivo
suelto del repositorio. get_or_create la hace idempotente.
"""
from django.db import migrations


FILENAME = '0c6qg0sg1qsfxhoth3srzf53i62neb-meta.html'
CONTENT = '0c6qg0sg1qsfxhoth3srzf53i62neb'


def seed_verification_file(apps, schema_editor):
    SiteVerificationFile = apps.get_model('seo', 'SiteVerificationFile')
    SiteVerificationFile.objects.get_or_create(
        filename=FILENAME,
        defaults=dict(
            name='Meta Business Verification (archivo HTML)',
            provider='meta',
            content=CONTENT,
            is_active=True,
        ),
    )


def remove_verification_file(apps, schema_editor):
    SiteVerificationFile = apps.get_model('seo', 'SiteVerificationFile')
    SiteVerificationFile.objects.filter(filename=FILENAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0003_verification_files'),
    ]

    operations = [
        migrations.RunPython(seed_verification_file, remove_verification_file),
    ]
