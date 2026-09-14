"""
White-label F9 (2026-08-14): la migracion de seed original
(0001_initial_squashed...::seed_renting_home_cards, antes 0019) sembro un
grupo de HomeCard llamado 'renting_home_brands' con 6 tarjetas nombrando
marcas de terceros reales del rubro de seguridad electronica (Hikvision,
Dahua, Ubiquiti, Cisco, Dell, APC) como si fueran "marcas y ecosistemas
compatibles" -- contenido de negocio especifico de Sintel, no generico de
plataforma, y ademas usa nombres de marcas reales de terceros sin relacion
declarada. Ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md
seccion 2.3.

NO se edita la migracion original (0001_initial_squashed) -- reescribir una
migracion ya aplicada no afecta instalaciones existentes (Django no vuelve a
correr una migracion ya registrada), asi que "corregir" el archivo viejo no
limpia los datos que ya sembro; hace falta esta migracion nueva y separada.

Desactiva (is_visible=False / is_active=False) en vez de borrar -- reversible,
y evita perder el historico si alguien ya lo customizo. Idempotente: si un
admin ya desactivo o edito estas filas, no las vuelve a activar ni pisa sus
cambios (solo actua sobre filas que siguen exactamente como las sembro el
seed original).
"""
from django.db import migrations

THIRD_PARTY_BRAND_TITLES = ['Hikvision', 'Dahua', 'Ubiquiti', 'Cisco', 'Dell', 'APC']


def deactivate_third_party_brand_cards(apps, schema_editor):
    HomeCard = apps.get_model('core', 'HomeCard')
    HomeCardGroup = apps.get_model('core', 'HomeCardGroup')

    HomeCard.objects.filter(
        group_name='renting_home_brands',
        title__in=THIRD_PARTY_BRAND_TITLES,
        is_active=True,
    ).update(is_active=False)

    # El grupo completo solo tenia estas 6 tarjetas de terceros -- se oculta
    # tambien, no solo las tarjetas, para no dejar un contenedor vacio visible
    # ("Marcas y ecosistemas compatibles" sin tarjetas adentro).
    HomeCardGroup.objects.filter(
        name='renting_home_brands',
        is_visible=True,
    ).update(is_visible=False)


def reactivate_third_party_brand_cards(apps, schema_editor):
    HomeCard = apps.get_model('core', 'HomeCard')
    HomeCardGroup = apps.get_model('core', 'HomeCardGroup')
    HomeCard.objects.filter(
        group_name='renting_home_brands', title__in=THIRD_PARTY_BRAND_TITLES,
    ).update(is_active=True)
    HomeCardGroup.objects.filter(name='renting_home_brands').update(is_visible=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_card_group_section_fields'),
    ]

    operations = [
        migrations.RunPython(deactivate_third_party_brand_cards, reactivate_third_party_brand_cards),
    ]
