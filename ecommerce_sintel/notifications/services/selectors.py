from notifications.models import NotificationTemplate, NotificationLog


class NotificationSelector:

    @staticmethod
    def list_templates():
        return NotificationTemplate.objects.filter(is_deleted=False).order_by('slug')

    @staticmethod
    def get_template_by_uuid(uuid):
        return NotificationTemplate.objects.filter(uuid=uuid, is_deleted=False).first()

    @staticmethod
    def list_logs(status=None, channel=None, template_slug=None, user_uuid=None):
        qs = (
            NotificationLog.objects
            .filter(is_deleted=False)
            .select_related('template', 'user')
            .order_by('-created_at')
        )
        if status:
            qs = qs.filter(status=status)
        if channel:
            qs = qs.filter(channel=channel)
        if template_slug:
            qs = qs.filter(template_slug__icontains=template_slug)
        if user_uuid:
            qs = qs.filter(user__uuid=user_uuid)
        return qs
