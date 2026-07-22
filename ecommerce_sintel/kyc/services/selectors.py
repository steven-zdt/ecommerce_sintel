from django.db.models import Avg, Count, F
from kyc.models import UserVerification, VerificationDocument


class KycSelector:

    @staticmethod
    def get_own_verification(user) -> UserVerification | None:
        return getattr(user, 'kyc_verification', None)

    @staticmethod
    def list_own_documents(verification: UserVerification):
        return verification.documents.filter(is_deleted=False).order_by('-created_at')

    @staticmethod
    def get_own_document(verification: UserVerification, uuid) -> VerificationDocument:
        return verification.documents.get(uuid=uuid, is_deleted=False)

    @staticmethod
    def list_queue(filters: dict | None = None):
        qs = UserVerification.objects.select_related('user', 'user__profile').filter(is_deleted=False)
        filters = filters or {}
        status = filters.get('status')
        if status:
            qs = qs.filter(status=status)
        requested_user_type = filters.get('requested_user_type')
        if requested_user_type:
            qs = qs.filter(requested_user_type=requested_user_type)
        search = filters.get('search')
        if search:
            qs = qs.filter(user__email__icontains=search)
        return qs.order_by('-created_at')

    @staticmethod
    def get_admin_metrics() -> dict:
        """
        Metricas para /panel/validaciones -- reemplaza el hack anterior del
        frontend (4 requests paginados leyendo solo .count). Mismo patron que
        accounts.services.selectors.ContractorAdminSelector.get_metrics().
        """
        base = UserVerification.objects.filter(is_deleted=False)
        by_status = dict(
            base.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        by_requested_type = dict(
            base.exclude(requested_user_type__isnull=True)
            .exclude(requested_user_type='')
            .values('requested_user_type').annotate(count=Count('id'))
            .values_list('requested_user_type', 'count')
        )
        # Tiempo promedio de aprobacion: solo verificaciones que SI pasaron por
        # submit-for-review (submitted_at) y ya fueron aprobadas -- no usar
        # first_approved_at, que se setea una sola vez en la vida del usuario
        # y no sirve para medir el ciclo de cada solicitud individual.
        avg_approval = base.filter(
            status=UserVerification.STATUS_APPROVED, submitted_at__isnull=False, reviewed_at__isnull=False,
        ).aggregate(avg_seconds=Avg(F('reviewed_at') - F('submitted_at')))['avg_seconds']

        return {
            'by_status': by_status,
            'by_requested_type': by_requested_type,
            'average_approval_seconds': avg_approval.total_seconds() if avg_approval else None,
        }

    @staticmethod
    def get_verification_for_admin(uuid) -> UserVerification:
        return UserVerification.objects.select_related('user', 'user__profile').prefetch_related(
            'documents', 'timeline_events',
        ).get(uuid=uuid, is_deleted=False)

    @staticmethod
    def get_timeline(verification: UserVerification):
        return verification.timeline_events.all().order_by('created_at')
