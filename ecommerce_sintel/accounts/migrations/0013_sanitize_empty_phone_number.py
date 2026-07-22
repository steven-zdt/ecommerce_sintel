from django.db import migrations


def sanitize_empty_phone_numbers(apps, schema_editor):
    """
    UserProfile.phone_number es unique=True; NULL puede repetirse bajo esa
    constraint pero '' (cadena vacia) no. Antes de que UserProfileUpdateSerializer
    normalizara '' -> None (auditoria QA 2026-07-19), guardar el perfil con
    telefono en blanco persistia '' literal -- la primera fila asi "envenenaba"
    la constraint: cualquier otro usuario que despues guardara con telefono
    vacio chocaba con IntegrityError 500. Esta migracion convierte cualquier
    fila existente con phone_number='' a NULL para que quede consistente con
    el nuevo comportamiento del serializer.
    """
    UserProfile = apps.get_model('accounts', 'UserProfile')
    UserProfile.objects.filter(phone_number='').update(phone_number=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_remove_userprofile_userprofile_document_unique_and_more'),
    ]

    operations = [
        migrations.RunPython(sanitize_empty_phone_numbers, reverse_code=noop_reverse),
    ]
