from django.db import migrations
from django.utils import timezone


def backfill_customer_approved(apps, schema_editor):
    """
    SSoT de identidad: un CUSTOMER nunca deberia necesitar KYC para operar
    (ver accounts/CLAUDE.md, "SSoT de identidad"). Antes de este cambio, el
    registro publico creaba a TODOS los usuarios (incluidos quienes solo
    querian comprar) en PENDING, bloqueando su login hasta aprobacion admin.
    Esta migracion corrige retroactivamente cualquier CUSTOMER que haya
    quedado atascado en ese estado -- idempotente (excluye a quien ya este
    APPROVED), sin efecto si ya no hay ninguno pendiente.
    """
    UserProfile = apps.get_model('accounts', 'UserProfile')
    UserVerification = apps.get_model('kyc', 'UserVerification')
    VerificationEvent = apps.get_model('kyc', 'VerificationEvent')

    now = timezone.now()
    stuck_user_ids = UserProfile.objects.filter(user_type='CUSTOMER').values_list('user_id', flat=True)
    qs = UserVerification.objects.filter(user_id__in=list(stuck_user_ids)).exclude(status='APPROVED')
    for verification in qs:
        verification.status = 'APPROVED'
        verification.reviewed_at = now
        if not verification.first_approved_at:
            verification.first_approved_at = now
        verification.save(update_fields=['status', 'reviewed_at', 'first_approved_at'])
        VerificationEvent.objects.create(
            verification=verification,
            event_type='APPROVED',
            description='Aprobacion retroactiva -- CUSTOMER nunca deberia requerir KYC.',
            actor=None,
            actor_email='',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('kyc', '0005_userverification_first_approved_at'),
        ('accounts', '0010_backfill_technician_profile_service_providers'),
    ]

    operations = [
        # Irreversible por diseno: no existe una necesidad operativa real de
        # "deshacer" una aprobacion retroactiva historica. La migracion hacia
        # adelante es idempotente, segura de re-ejecutar.
        migrations.RunPython(backfill_customer_approved, reverse_code=migrations.RunPython.noop),
    ]
