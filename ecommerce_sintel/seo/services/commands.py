from django.core.exceptions import ValidationError
from django.db import transaction

from seo.models import SiteMetaTag, SeoMetaTagAuditLog, SiteVerificationFile

VERIFICATION_FILE_MUTABLE_FIELDS = ('name', 'provider', 'filename', 'content', 'is_active')

MUTABLE_FIELDS = (
    'name', 'provider', 'tag_type', 'description', 'meta_name', 'meta_content',
    'html_snippet', 'priority', 'is_active', 'target_page', 'environment',
)


class MetaTagCommands:
    """
    Unico punto de escritura de SiteMetaTag / SeoMetaTagAuditLog. Los
    ViewSets (dashboard/api/views.py) validan con MetaTagInputSerializer y
    pasan `serializer.validated_data` aqui -- nunca escriben el modelo
    directamente (mismo patron que core.services.commands.AboutUsCommands).
    """

    @staticmethod
    def _resolve_user_and_ip(request):
        """Mismo criterio que security/services/commands.py::log_event."""
        user = None
        ip_address = None
        if request is not None:
            req_user = getattr(request, 'user', None)
            if req_user is not None and getattr(req_user, 'is_authenticated', False):
                user = req_user
            ip_address = request.META.get('REMOTE_ADDR')
        return user, ip_address

    @staticmethod
    def _log(meta_tag, action, request, changes=None):
        user, ip_address = MetaTagCommands._resolve_user_and_ip(request)
        SeoMetaTagAuditLog.objects.create(
            meta_tag=meta_tag,
            meta_tag_name=meta_tag.name if meta_tag else '',
            action=action,
            user=user,
            ip_address=ip_address,
            changes=changes or {},
        )

    @staticmethod
    def _assert_not_duplicate(provider, meta_name, exclude_uuid=None):
        if not meta_name:
            return
        qs = SiteMetaTag.objects.filter(
            provider=provider, meta_name__iexact=meta_name,
            is_active=True, is_deleted=False,
        )
        if exclude_uuid:
            qs = qs.exclude(uuid=exclude_uuid)
        if qs.exists():
            raise ValidationError({
                'meta_name': [f'Ya existe una metaetiqueta activa de "{provider}" con meta_name "{meta_name}".'],
            })

    @staticmethod
    @transaction.atomic
    def create(data: dict, request=None) -> SiteMetaTag:
        clean_data = {k: v for k, v in data.items() if k in MUTABLE_FIELDS}
        MetaTagCommands._assert_not_duplicate(clean_data.get('provider'), clean_data.get('meta_name'))

        user, _ = MetaTagCommands._resolve_user_and_ip(request)
        tag = SiteMetaTag(**clean_data)
        tag.created_by = user
        tag.updated_by = user
        tag.full_clean()
        tag.save()
        MetaTagCommands._log(tag, SeoMetaTagAuditLog.ACTION_CREATED, request, changes=clean_data)
        return tag

    @staticmethod
    @transaction.atomic
    def update(tag: SiteMetaTag, data: dict, request=None) -> SiteMetaTag:
        clean_data = {k: v for k, v in data.items() if k in MUTABLE_FIELDS}
        MetaTagCommands._assert_not_duplicate(
            clean_data.get('provider', tag.provider),
            clean_data.get('meta_name', tag.meta_name),
            exclude_uuid=tag.uuid,
        )

        user, _ = MetaTagCommands._resolve_user_and_ip(request)
        for key, value in clean_data.items():
            setattr(tag, key, value)
        tag.updated_by = user
        tag.full_clean()
        tag.save()
        MetaTagCommands._log(tag, SeoMetaTagAuditLog.ACTION_UPDATED, request, changes=clean_data)
        return tag

    @staticmethod
    @transaction.atomic
    def delete(tag: SiteMetaTag, request=None) -> None:
        tag.is_active = False
        tag.is_deleted = True
        tag.save(update_fields=['is_active', 'is_deleted', 'updated_at'])
        MetaTagCommands._log(tag, SeoMetaTagAuditLog.ACTION_DELETED, request)

    @staticmethod
    @transaction.atomic
    def duplicate(tag: SiteMetaTag, request=None) -> SiteMetaTag:
        """La copia nace inactiva -- evita chocar con el chequeo de duplicados
        activos y obliga al admin a revisarla antes de publicarla."""
        user, _ = MetaTagCommands._resolve_user_and_ip(request)
        copy = SiteMetaTag(
            name=f'{tag.name} (copia)',
            provider=tag.provider,
            tag_type=tag.tag_type,
            description=tag.description,
            meta_name=tag.meta_name,
            meta_content=tag.meta_content,
            html_snippet=tag.html_snippet,
            priority=tag.priority,
            is_active=False,
            target_page=tag.target_page,
            environment=tag.environment,
            created_by=user,
            updated_by=user,
        )
        copy.full_clean()
        copy.save()
        MetaTagCommands._log(
            copy, SeoMetaTagAuditLog.ACTION_DUPLICATED, request,
            changes={'source_uuid': str(tag.uuid)},
        )
        return copy

    @staticmethod
    @transaction.atomic
    def toggle_active(tag: SiteMetaTag, request=None) -> SiteMetaTag:
        new_state = not tag.is_active
        if new_state:
            MetaTagCommands._assert_not_duplicate(tag.provider, tag.meta_name, exclude_uuid=tag.uuid)
        tag.is_active = new_state
        tag.save(update_fields=['is_active', 'updated_at'])
        action = SeoMetaTagAuditLog.ACTION_ACTIVATED if new_state else SeoMetaTagAuditLog.ACTION_DEACTIVATED
        MetaTagCommands._log(tag, action, request)
        return tag

    @staticmethod
    @transaction.atomic
    def reorder(ordered_uuids: list, request=None) -> None:
        for index, uuid_value in enumerate(ordered_uuids):
            SiteMetaTag.objects.filter(uuid=uuid_value, is_deleted=False).update(priority=index)
        MetaTagCommands._log(
            None, SeoMetaTagAuditLog.ACTION_REORDERED, request,
            changes={'order': [str(u) for u in ordered_uuids]},
        )

    @staticmethod
    def export(queryset=None, request=None) -> list:
        queryset = queryset if queryset is not None else SiteMetaTag.objects.filter(is_deleted=False)
        data = [
            {
                'name': t.name, 'provider': t.provider, 'tag_type': t.tag_type,
                'description': t.description, 'meta_name': t.meta_name,
                'meta_content': t.meta_content, 'html_snippet': t.html_snippet,
                'priority': t.priority, 'is_active': t.is_active,
                'target_page': t.target_page, 'environment': t.environment,
            }
            for t in queryset
        ]
        MetaTagCommands._log(None, SeoMetaTagAuditLog.ACTION_EXPORTED, request, changes={'count': len(data)})
        return data

    @staticmethod
    def log_import(count: int, request=None) -> None:
        MetaTagCommands._log(None, SeoMetaTagAuditLog.ACTION_IMPORTED, request, changes={'count': count})


class VerificationFileCommands:
    """
    Unico punto de escritura de SiteVerificationFile -- archivos estaticos
    servidos en la raiz del dominio (metodo "Subir archivo HTML" de
    verificacion, alternativo a la metaetiqueta). Auditoria reusa
    SeoMetaTagAuditLog con meta_tag=None (mismo criterio que reorder/export/
    import de MetaTagCommands para acciones sin un SiteMetaTag puntual).
    """

    @staticmethod
    def _log(action, request, filename, changes=None):
        user, ip_address = MetaTagCommands._resolve_user_and_ip(request)
        SeoMetaTagAuditLog.objects.create(
            meta_tag=None, meta_tag_name=f'[verification_file] {filename}',
            action=action, user=user, ip_address=ip_address, changes=changes or {},
        )

    @staticmethod
    @transaction.atomic
    def create(data: dict, request=None) -> SiteVerificationFile:
        clean_data = {k: v for k, v in data.items() if k in VERIFICATION_FILE_MUTABLE_FIELDS}
        user, _ = MetaTagCommands._resolve_user_and_ip(request)
        record = SiteVerificationFile(**clean_data)
        record.created_by = user
        record.updated_by = user
        record.full_clean()
        record.save()
        VerificationFileCommands._log(SeoMetaTagAuditLog.ACTION_CREATED, request, record.filename, changes=clean_data)
        return record

    @staticmethod
    @transaction.atomic
    def update(record: SiteVerificationFile, data: dict, request=None) -> SiteVerificationFile:
        clean_data = {k: v for k, v in data.items() if k in VERIFICATION_FILE_MUTABLE_FIELDS}
        user, _ = MetaTagCommands._resolve_user_and_ip(request)
        for key, value in clean_data.items():
            setattr(record, key, value)
        record.updated_by = user
        record.full_clean()
        record.save()
        VerificationFileCommands._log(SeoMetaTagAuditLog.ACTION_UPDATED, request, record.filename, changes=clean_data)
        return record

    @staticmethod
    @transaction.atomic
    def delete(record: SiteVerificationFile, request=None) -> None:
        filename = record.filename
        record.is_active = False
        record.is_deleted = True
        record.save(update_fields=['is_active', 'is_deleted', 'updated_at'])
        VerificationFileCommands._log(SeoMetaTagAuditLog.ACTION_DELETED, request, filename)

    @staticmethod
    @transaction.atomic
    def toggle_active(record: SiteVerificationFile, request=None) -> SiteVerificationFile:
        record.is_active = not record.is_active
        record.save(update_fields=['is_active', 'updated_at'])
        action = SeoMetaTagAuditLog.ACTION_ACTIVATED if record.is_active else SeoMetaTagAuditLog.ACTION_DEACTIVATED
        VerificationFileCommands._log(action, request, record.filename)
        return record
