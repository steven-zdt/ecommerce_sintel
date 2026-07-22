from django.db import migrations
from django.utils import timezone


def grandfather_approve_existing_users(apps, schema_editor):
    """
    Usuarios que ya existian antes de introducir KYC nunca pasaron por el
    flujo de registro nuevo, asi que no tienen UserVerification. Sin esta
    migracion, el gate de login (verification_status == APPROVED) los
    dejaria bloqueados de un dia para otro. Se les crea retroactivamente una
    UserVerification en APPROVED -- idempotente (get_or_create), no fabrica
    ConsentRecord (seria deshonesto simular un consentimiento que nunca
    dieron; backfill de eso es un ejercicio legal aparte, fuera de alcance).
    """
    User = apps.get_model('users', 'User')
    UserVerification = apps.get_model('kyc', 'UserVerification')
    VerificationEvent = apps.get_model('kyc', 'VerificationEvent')

    now = timezone.now()
    for user in User.objects.filter(is_active=True, kyc_verification__isnull=True):
        verification, created = UserVerification.objects.get_or_create(
            user=user,
            defaults={'status': 'APPROVED', 'reviewed_at': now},
        )
        if created:
            VerificationEvent.objects.create(
                verification=verification,
                event_type='APPROVED',
                description='Aprobacion retroactiva (usuario previo a KYC).',
                actor=None,
                actor_email='',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('kyc', '0002_seed_notification_templates'),
    ]

    operations = [
        # Irreversible por diseno: no existe una necesidad operativa real de
        # "deshacer" una aprobacion retroactiva historica. La migracion hacia
        # adelante es idempotente (get_or_create), segura de re-ejecutar.
        migrations.RunPython(grandfather_approve_existing_users, reverse_code=migrations.RunPython.noop),
    ]
