from django.db import migrations


def backfill_footer_groups(apps, schema_editor):
    FooterLink = apps.get_model('core', 'FooterLink')
    FooterGroup = apps.get_model('core', 'FooterGroup')

    # Cubre TODAS las filas (incluidas category='social' e is_deleted=True) porque
    # `group` pasa a ser NOT NULL en la migracion siguiente -- filas legadas/soft-deleted
    # tambien necesitan un grupo valido o el ALTER falla con IntegrityError.
    links = FooterLink.objects.all().order_by('group_name', 'display_order')
    distinct_names = []
    for link in links:
        name = link.group_name or 'Otros'
        if name not in distinct_names:
            distinct_names.append(name)

    groups_by_name = {}
    for index, name in enumerate(distinct_names):
        groups_by_name[name] = FooterGroup.objects.create(title=name, display_order=index)

    for link in links:
        name = link.group_name or 'Otros'
        link.group = groups_by_name[name]
        link.save(update_fields=['group'])


def noop_reverse(apps, schema_editor):
    """Irreversible a proposito: recrear group_name desde FooterGroup.title perderia
    la distincion original entre grupos con el mismo titulo. No hay rollback de datos."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_footergroup'),
    ]

    operations = [
        migrations.RunPython(backfill_footer_groups, noop_reverse),
    ]
