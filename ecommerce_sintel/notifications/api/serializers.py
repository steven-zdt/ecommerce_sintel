from rest_framework import serializers
from notifications.models import NotificationLog, NotificationTemplate, UserNotificationPreference


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationTemplate
        fields = [
            'uuid', 'slug', 'name', 'subject', 'email_body',
            'whatsapp_template_name', 'ws_event_type', 'is_active', 'created_at',
        ]
        read_only_fields = ['uuid', 'slug', 'created_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    # NotificationLog.template_slug (no template.slug via FK): se poblo para que
    # sobreviva aunque `template` sea None (slug roto/inactivo -- ver
    # NotificationCommands.dispatch_notification). source='template.slug'
    # rompia con AttributeError en esas filas.
    class Meta:
        model  = NotificationLog
        fields = [
            'uuid', 'template_slug', 'channel', 'status',
            'sent_at', 'error_message', 'created_at',
        ]


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserNotificationPreference
        fields = ['uuid', 'channel', 'is_enabled']
