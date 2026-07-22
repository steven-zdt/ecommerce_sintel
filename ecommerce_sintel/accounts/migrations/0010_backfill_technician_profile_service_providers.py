from django.db import migrations

SERVICE_PROVIDER_TYPES = {'TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR'}


def backfill_technician_profiles(apps, schema_editor):
    """
    El signal post_save de UserProfile que auto-crea TechnicianProfile se generalizo de
    solo TECHNICIAN a los 4 tipos service-provider (Fase 2 del marketplace de contratistas,
    2026-07-05), pero los signals no aplican retroactivamente a filas ya existentes. Esta
    migracion backfillea TechnicianProfile para los perfiles PROFESSIONAL/SPECIALIST/CONTRACTOR
    creados antes del fix, para que queden asignables igual que los TECHNICIAN.
    """
    UserProfile = apps.get_model('accounts', 'UserProfile')
    TechnicianProfile = apps.get_model('accounts', 'TechnicianProfile')

    missing = UserProfile.objects.filter(
        is_deleted=False,
        user_type__in=SERVICE_PROVIDER_TYPES,
        user__technician_profile__isnull=True,
    )
    for profile in missing:
        TechnicianProfile.objects.get_or_create(user=profile.user)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_seed_admin_user_notification_templates'),
    ]

    operations = [
        migrations.RunPython(backfill_technician_profiles, reverse_code=noop_reverse),
    ]
