"""
Data migration: transfiere datos de perfiles desde users hacia accounts.

Ordena las operaciones para preservar integridad referencial:
  1. Crea accounts.UserProfile por cada User (copia first_name, last_name,
     phone_number del User y address/city/… del users.UserProfile antiguo).
  2. Crea accounts.VendorProfile copiando users.VendorProfile.
  3. Crea accounts.TechnicianProfile copiando users.TechnicianProfile
     (incluyendo la M2M specialties).
"""
from django.db import migrations


def migrate_forward(apps, schema_editor):
    User = apps.get_model('users', 'User')

    OldUserProfile = apps.get_model('users', 'UserProfile')
    NewUserProfile = apps.get_model('accounts', 'UserProfile')

    OldVendorProfile = apps.get_model('users', 'VendorProfile')
    NewVendorProfile = apps.get_model('accounts', 'VendorProfile')

    OldTechnicianProfile = apps.get_model('users', 'TechnicianProfile')
    NewTechnicianProfile = apps.get_model('accounts', 'TechnicianProfile')

    # -- UserProfile -------------------------------------------------------
    old_profiles = {op.user_id: op for op in OldUserProfile.objects.all()}

    for user in User.objects.all():
        old = old_profiles.get(user.pk)
        NewUserProfile.objects.get_or_create(
            user=user,
            defaults={
                'first_name': getattr(user, 'first_name', '') or '',
                'last_name': getattr(user, 'last_name', '') or '',
                'phone_number': getattr(user, 'phone_number', None),
                'profile_picture': old.profile_picture if old else None,
                'address': old.address if old else None,
                'city': old.city if old else None,
                'state': old.state if old else None,
                'country': old.country if old else None,
                'postal_code': old.postal_code if old else None,
            },
        )

    # -- VendorProfile -----------------------------------------------------
    for old_vp in OldVendorProfile.objects.all():
        NewVendorProfile.objects.get_or_create(
            user=old_vp.user,
            defaults={
                'store_name': old_vp.store_name,
                'business_license': old_vp.business_license,
                'address': old_vp.address,
                'business_phone': old_vp.business_phone,
            },
        )

    # -- TechnicianProfile + M2M specialties --------------------------------
    for old_tp in OldTechnicianProfile.objects.prefetch_related('specialties').all():
        new_tp, _ = NewTechnicianProfile.objects.get_or_create(
            user=old_tp.user,
            defaults={'is_available': old_tp.is_available},
        )
        new_tp.specialties.set(old_tp.specialties.all())


def migrate_backward(apps, schema_editor):
    apps.get_model('accounts', 'UserProfile').objects.all().delete()
    apps.get_model('accounts', 'VendorProfile').objects.all().delete()
    apps.get_model('accounts', 'TechnicianProfile').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_create_profiles"),
        ("users", "0003_alter_user_role_technicianprofile"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
