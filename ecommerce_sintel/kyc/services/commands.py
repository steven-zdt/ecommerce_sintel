import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from kyc.models import UserVerification, VerificationDocument, VerificationEvent, ConsentRecord
from kyc.services.config import ALLOWED_TRANSITIONS, STATUS_TO_EVENT_TYPE, DOC_TYPE_LIMITS, get_required_doc_types
from kyc.services.scanner import DocumentScanner

logger = logging.getLogger(__name__)


def _audit_log(actor, target_user, action: str, metadata: dict = None) -> None:
    """
    Dual-log: ademas del VerificationEvent (detalle fino, propio de kyc), se
    registra tambien en users.UserAuditLog para que el tab de auditoria de
    /panel/usuarios muestre los eventos KYC junto con el resto de acciones
    administrativas sobre el usuario.
    """
    from users.services.commands import UserAuditCommands
    UserAuditCommands.log(actor=actor, target_user=target_user, action=action, metadata=metadata or {})


def _dispatch(user, slug: str, context: dict, ws_group: str = None) -> None:
    from notifications.services.commands import NotificationCommands
    group = ws_group or f'user_{user.uuid}'
    NotificationCommands.dispatch_notification(
        user=user,
        template_slug=slug,
        context=context,
        ws_group=group,
    )


def _missing_required_doc_types(verification: UserVerification) -> list:
    required = get_required_doc_types(verification.requested_user_type)
    present = set(
        verification.documents.filter(
            is_deleted=False, doc_type__in=required,
        ).values_list('doc_type', flat=True)
    )
    return [doc_type for doc_type in required if doc_type not in present]


def _all_required_docs_approved(verification: UserVerification) -> list:
    """Retorna la lista de doc_types requeridos que AUN NO tienen un documento aprobado."""
    missing = []
    for doc_type in get_required_doc_types(verification.requested_user_type):
        approved = verification.documents.filter(
            is_deleted=False, doc_type=doc_type, status=VerificationDocument.STATUS_APPROVED,
        ).exists()
        if not approved:
            missing.append(doc_type)
    return missing


class KycCommands:

    @staticmethod
    @transaction.atomic
    def bootstrap_approved(user, kyc_fields: dict = None, consent_events: list = None) -> UserVerification:
        """
        Crea una UserVerification ya APPROVED, sin pasar por revision admin.
        Dos callers distintos:
        1. Cuentas creadas directamente por un admin (UserAdminCreateSerializer
           / /panel/usuarios) o codigo interno (tests, fixtures) -- sin
           kyc_fields/consent_events, ya son confiables por construccion.
        2. SSoT de identidad: todo registro publico nuevo (CUSTOMER, via
           AccountCommands.register_user/create_from_verified_payload) --
           SI trae kyc_fields/consent_events, porque un CUSTOMER igual declara
           su identidad y acepta Habeas Data en el registro, solo que ya no
           necesita esperar revision admin para poder operar (a diferencia de
           quien pide un upgrade a profesional via KycCommands.request_upgrade,
           que si vuelve a PENDING).
        """
        verification = UserVerification.objects.create(
            user=user, status=UserVerification.STATUS_APPROVED,
            reviewed_at=timezone.now(), first_approved_at=timezone.now(),
            **(kyc_fields or {}),
        )

        for event in (consent_events or []):
            ConsentRecord.objects.create(
                user=user,
                consent_type=event['consent_type'],
                document_version=event['document_version'],
                ip_address=event['ip_address'],
                user_agent=event.get('user_agent', ''),
            )

        VerificationEvent.objects.create(
            verification=verification,
            event_type=VerificationEvent.APPROVED,
            description='Cuenta creada directamente (sin revision admin -- CUSTOMER o creacion admin).',
            actor=None,
            actor_email='',
        )
        logger.info(f"[kyc:bootstrap_approved] Verificacion auto-aprobada para {user.email}")
        return verification

    @staticmethod
    @transaction.atomic
    def upload_document(verification: UserVerification, doc_type: str, file, uploaded_by) -> VerificationDocument:
        from accounts.services.commands import validate_file
        max_size_mb, allowed_extensions = DOC_TYPE_LIMITS.get(doc_type, (5, ['.pdf', '.jpg', '.jpeg', '.png']))
        validate_file(file, max_size_mb=max_size_mb, allowed_extensions=allowed_extensions, magic_bytes_check=True)

        file_hash = DocumentScanner.sha256_of(file)
        scan_result = DocumentScanner.scan(file)

        doc = VerificationDocument.objects.create(
            verification=verification,
            doc_type=doc_type,
            file=file,
            original_filename=file.name,
            content_type=getattr(file, 'content_type', '') or '',
            file_hash_sha256=file_hash,
            scan_status=scan_result.status,
            uploaded_by=uploaded_by,
        )

        VerificationEvent.objects.create(
            verification=verification,
            event_type=VerificationEvent.DOC_UPLOADED,
            document=doc,
            actor=uploaded_by,
            actor_email=getattr(uploaded_by, 'email', ''),
        )
        logger.info(f"[kyc:upload_document] {verification.user.email} | {doc_type} | doc={doc.uuid}")
        return doc

    @staticmethod
    @transaction.atomic
    def delete_document(document: VerificationDocument, requesting_user) -> None:
        verification = document.verification
        if verification.status not in (UserVerification.STATUS_PENDING, UserVerification.STATUS_REJECTED):
            raise ValidationError(
                "No se pueden eliminar documentos mientras la verificacion esta en revision o ya fue aprobada."
            )
        # Soft-delete unicamente -- el archivo nunca se borra del disco, nunca
        # se destruye evidencia de lo que el usuario subio.
        document.is_deleted = True
        document.save(update_fields=['is_deleted', 'updated_at'])

        VerificationEvent.objects.create(
            verification=verification,
            event_type=VerificationEvent.DOC_DELETED,
            document=document,
            actor=requesting_user,
            actor_email=getattr(requesting_user, 'email', ''),
        )
        logger.info(f"[kyc:delete_document] {verification.user.email} | doc={document.uuid}")

    @staticmethod
    @transaction.atomic
    def submit_for_review(verification: UserVerification, by) -> UserVerification:
        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        if verification.status not in (UserVerification.STATUS_PENDING, UserVerification.STATUS_REJECTED):
            raise ValidationError(
                f"No se puede enviar a revision desde el estado {verification.status}."
            )
        missing = _missing_required_doc_types(verification)
        if missing:
            raise ValidationError(
                {'documents': f"Faltan documentos obligatorios: {', '.join(missing)}."}
            )

        verification.submitted_at = timezone.now()
        verification.save(update_fields=['submitted_at', 'updated_at'])
        KycCommands._transition(verification, UserVerification.STATUS_UNDER_REVIEW, by=by)
        _audit_log(actor=by, target_user=verification.user, action='kyc_submitted')

        transaction.on_commit(
            lambda: _dispatch(
                user=verification.user,
                slug='kyc_submitted_for_review',
                context={'user_email': verification.user.email},
                ws_group='admin_notifications',
            )
        )
        return verification

    @staticmethod
    @transaction.atomic
    def approve(verification: UserVerification, reviewed_by) -> UserVerification:
        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        if verification.status != UserVerification.STATUS_UNDER_REVIEW:
            raise ValidationError(f"Solo se puede aprobar desde UNDER_REVIEW (actual: {verification.status}).")
        missing = _all_required_docs_approved(verification)
        if missing:
            raise ValidationError(
                {'documents': f"Aun faltan documentos requeridos por aprobar: {', '.join(missing)}."}
            )

        verification.reviewed_by = reviewed_by
        verification.reviewed_at = timezone.now()
        if verification.first_approved_at is None:
            verification.first_approved_at = timezone.now()
        verification.save(update_fields=['reviewed_by', 'reviewed_at', 'first_approved_at', 'updated_at'])
        KycCommands._transition(verification, UserVerification.STATUS_APPROVED, by=reviewed_by)
        KycCommands._apply_requested_user_type(verification)
        _audit_log(actor=reviewed_by, target_user=verification.user, action='kyc_approved')

        transaction.on_commit(
            lambda: _dispatch(
                user=verification.user,
                slug='kyc_approved',
                context={'user_email': verification.user.email},
            )
        )
        return verification

    @staticmethod
    @transaction.atomic
    def force_approve(verification: UserVerification, reviewed_by, note: str = '') -> UserVerification:
        """
        Aprobacion manual de administrador -- a diferencia de approve(), NO
        exige que cada documento requerido este individualmente aprobado, ni
        pasa por ALLOWED_TRANSITIONS (permite PENDING/UNDER_REVIEW/REJECTED
        -> APPROVED directo). Pensada para el panel /panel/usuarios, donde
        un admin puede querer activar a alguien de inmediato sin recorrer el
        flujo completo de revision documento por documento. Queda registrado
        de forma explicita como override manual, tanto en el timeline propio
        (VerificationEvent) como en el audit log general (UserAuditLog), para
        que nunca se confunda con una aprobacion via el flujo normal.
        """
        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        if verification.status not in (
            UserVerification.STATUS_PENDING,
            UserVerification.STATUS_UNDER_REVIEW,
            UserVerification.STATUS_REJECTED,
        ):
            raise ValidationError(
                f"No se puede aprobar manualmente desde el estado {verification.status}."
            )

        verification.status = UserVerification.STATUS_APPROVED
        verification.reviewed_by = reviewed_by
        verification.reviewed_at = timezone.now()
        if verification.first_approved_at is None:
            verification.first_approved_at = timezone.now()
        verification.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'first_approved_at', 'updated_at'])

        description = 'Aprobacion manual por administrador (no exige documentos revisados).'
        if note:
            description += f' Nota: {note}'
        VerificationEvent.objects.create(
            verification=verification,
            event_type=VerificationEvent.APPROVED,
            description=description,
            actor=reviewed_by,
            actor_email=getattr(reviewed_by, 'email', ''),
        )
        KycCommands._apply_requested_user_type(verification)
        _audit_log(
            actor=reviewed_by, target_user=verification.user, action='kyc_approved',
            metadata={'manual_override': True, 'note': note},
        )

        transaction.on_commit(
            lambda: _dispatch(
                user=verification.user,
                slug='kyc_approved',
                context={'user_email': verification.user.email},
            )
        )
        return verification

    @staticmethod
    @transaction.atomic
    def request_upgrade(verification: UserVerification, requested_user_type: str, by) -> UserVerification:
        """
        Un CUSTOMER ya APPROVED pide convertirse en profesional
        (CONTRACTOR/PROFESSIONAL/SPECIALIST/TECHNICIAN). Reabre la MISMA fila
        de verificacion (OneToOne, una sola vez por usuario) en vez de crear
        una segunda -- bypassa ALLOWED_TRANSITIONS igual que force_approve()
        (caso especial documentado, no se toca la tabla generica) porque
        APPROVED -> PENDING no es una transicion valida para el flujo normal
        de revision admin, pero si para arrancar un nuevo ciclo de subida de
        documentos. reviewed_at NO se borra (ver
        AccountCommands._assert_kyc_approved: el usuario conserva su acceso
        de comprador mientras se revisa el ascenso).
        """
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES

        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        if verification.status != UserVerification.STATUS_APPROVED:
            raise ValidationError(
                f"Solo se puede solicitar un upgrade desde APPROVED (actual: {verification.status})."
            )
        if requested_user_type not in SERVICE_PROVIDER_TYPES:
            raise ValidationError({'requested_user_type': 'Tipo de perfil profesional invalido.'})

        verification.requested_user_type = requested_user_type
        verification.status = UserVerification.STATUS_PENDING
        verification.submitted_at = None
        verification.save(update_fields=['requested_user_type', 'status', 'submitted_at', 'updated_at'])

        VerificationEvent.objects.create(
            verification=verification,
            event_type=VerificationEvent.NOTE,
            description=f'Solicitud de upgrade a {requested_user_type}.',
            actor=by,
            actor_email=getattr(by, 'email', ''),
        )
        _audit_log(
            actor=by, target_user=verification.user, action='kyc_upgrade_requested',
            metadata={'requested_user_type': requested_user_type},
        )
        logger.info(f"[kyc:request_upgrade] {verification.user.email} -> {requested_user_type}")
        return verification

    @staticmethod
    def _apply_requested_user_type(verification: UserVerification) -> None:
        """
        Efecto secundario de approve()/force_approve(): si esta verificacion
        tenia una solicitud de upgrade pendiente (KycCommands.request_upgrade),
        este es el UNICO lugar del sistema que actualiza
        accounts.UserProfile.user_type -- nunca antes de que el KYC termine
        correctamente. Dispara gratis la senal existente que crea
        TechnicianProfile (accounts/models.py).

        Tambien asigna un Django Group con el nombre del tipo aprobado --
        puramente cosmetico, para que /panel/usuarios lo refleje. Los
        Groups no tienen ningun efecto en la autorizacion real del sistema
        (eso sigue siendo 100% ProfileResolver/user_type via
        users/api/permissions.py) -- no reemplazan ni alimentan ningun
        permission class.
        """
        if not verification.requested_user_type:
            return
        from django.contrib.auth.models import Group
        profile = verification.user.profile
        profile.user_type = verification.requested_user_type
        profile.save(update_fields=['user_type'])
        group, _ = Group.objects.get_or_create(name=verification.requested_user_type)
        verification.user.groups.add(group)
        logger.info(
            f"[kyc:apply_requested_user_type] {verification.user.email} -> {verification.requested_user_type}"
        )

    @staticmethod
    @transaction.atomic
    def reject(verification: UserVerification, reviewed_by, reason: str) -> UserVerification:
        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        if verification.status != UserVerification.STATUS_UNDER_REVIEW:
            raise ValidationError(f"Solo se puede rechazar desde UNDER_REVIEW (actual: {verification.status}).")
        if not reason:
            raise ValidationError({'reason': 'Debes indicar el motivo del rechazo.'})

        verification.reviewed_by = reviewed_by
        verification.reviewed_at = timezone.now()
        verification.admin_message = reason
        verification.save(update_fields=['reviewed_by', 'reviewed_at', 'admin_message', 'updated_at'])
        KycCommands._transition(verification, UserVerification.STATUS_REJECTED, by=reviewed_by, description=reason)
        _audit_log(actor=reviewed_by, target_user=verification.user, action='kyc_rejected', metadata={'reason': reason})

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.KYC_REJECTED, user=verification.user, severity=SecurityEvent.SEVERITY_WARNING,
            metadata={'reason': reason, 'reviewed_by': getattr(reviewed_by, 'email', None)},
        )

        transaction.on_commit(
            lambda: _dispatch(
                user=verification.user,
                slug='kyc_rejected',
                context={'user_email': verification.user.email, 'reason': reason},
            )
        )
        return verification

    @staticmethod
    @transaction.atomic
    def request_more_info(verification: UserVerification, reviewed_by, message: str) -> UserVerification:
        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        if verification.status != UserVerification.STATUS_UNDER_REVIEW:
            raise ValidationError(
                f"Solo se puede solicitar informacion desde UNDER_REVIEW (actual: {verification.status})."
            )
        verification.admin_message = message
        verification.save(update_fields=['admin_message', 'updated_at'])
        KycCommands._transition(verification, UserVerification.STATUS_PENDING, by=reviewed_by, description=message)
        _audit_log(actor=reviewed_by, target_user=verification.user, action='kyc_info_requested', metadata={'message': message})

        transaction.on_commit(
            lambda: _dispatch(
                user=verification.user,
                slug='kyc_info_requested',
                context={'user_email': verification.user.email, 'message': message},
            )
        )
        return verification

    @staticmethod
    @transaction.atomic
    def block(verification: UserVerification, reviewed_by, reason: str) -> UserVerification:
        verification = UserVerification.objects.select_for_update().get(pk=verification.pk)
        allowed_from = (
            UserVerification.STATUS_PENDING,
            UserVerification.STATUS_UNDER_REVIEW,
            UserVerification.STATUS_APPROVED,
        )
        if verification.status not in allowed_from:
            raise ValidationError(f"No se puede bloquear desde el estado {verification.status}.")

        verification.admin_message = reason
        verification.save(update_fields=['admin_message', 'updated_at'])
        # No se toca user.is_active -- eso sigue siendo una decision admin
        # separada y ya existente (UserViewSet); bloquear es un estado KYC
        # que el gate de login ya verifica.
        KycCommands._transition(verification, UserVerification.STATUS_BLOCKED, by=reviewed_by, description=reason)
        _audit_log(actor=reviewed_by, target_user=verification.user, action='kyc_blocked', metadata={'reason': reason})

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.KYC_BLOCKED, user=verification.user, severity=SecurityEvent.SEVERITY_CRITICAL,
            metadata={'reason': reason, 'reviewed_by': getattr(reviewed_by, 'email', None)},
        )

        transaction.on_commit(
            lambda: _dispatch(
                user=verification.user,
                slug='kyc_blocked',
                context={'user_email': verification.user.email, 'reason': reason},
            )
        )
        return verification

    @staticmethod
    @transaction.atomic
    def review_document(document: VerificationDocument, approved: bool, reviewed_by, reason: str = '') -> VerificationDocument:
        document.status = VerificationDocument.STATUS_APPROVED if approved else VerificationDocument.STATUS_REJECTED
        document.reviewed_by = reviewed_by
        document.reviewed_at = timezone.now()
        document.rejection_reason = '' if approved else reason
        document.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'updated_at'])

        VerificationEvent.objects.create(
            verification=document.verification,
            event_type=VerificationEvent.DOC_APPROVED if approved else VerificationEvent.DOC_REJECTED,
            document=document,
            description=reason,
            actor=reviewed_by,
            actor_email=getattr(reviewed_by, 'email', ''),
        )
        return document

    @staticmethod
    def mark_document_opened(document: VerificationDocument, admin_user) -> None:
        VerificationEvent.objects.create(
            verification=document.verification,
            event_type=VerificationEvent.DOC_OPENED,
            document=document,
            actor=admin_user,
            actor_email=getattr(admin_user, 'email', ''),
        )

    @staticmethod
    def _transition(verification: UserVerification, new_status: str, by=None, description: str = '') -> None:
        previous_status = verification.status
        allowed = ALLOWED_TRANSITIONS.get(previous_status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"Transicion invalida: {previous_status} -> {new_status}. Permitidas: {allowed}"
            )
        verification.status = new_status
        verification.save(update_fields=['status', 'updated_at'])

        event_type = STATUS_TO_EVENT_TYPE.get(new_status, VerificationEvent.NOTE)
        VerificationEvent.objects.create(
            verification=verification,
            event_type=event_type,
            description=description,
            actor=by,
            actor_email=getattr(by, 'email', ''),
        )
