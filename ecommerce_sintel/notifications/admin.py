from django.contrib import admin
from notifications.models import (
    NotificationTemplate,
    UserNotificationPreference,
    NotificationLog,
    MetaWebhookEvent,
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display  = ('slug', 'name', 'ws_event_type', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('slug', 'name', 'ws_event_type')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('slug', 'name', 'is_active')}),
        ('WebSocket', {'fields': ('ws_event_type',)}),
        ('Email', {'fields': ('subject', 'email_body'), 'classes': ('collapse',)}),
        ('WhatsApp', {'fields': ('whatsapp_template_name',), 'classes': ('collapse',)}),
        ('SMS', {'fields': ('sms_body',), 'classes': ('collapse',)}),
        ('Auditoria', {'fields': ('uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display  = ('user', 'channel', 'is_enabled', 'created_at')
    list_filter   = ('channel', 'is_enabled')
    search_fields = ('user__email',)
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    # N-06 (auditoria enterprise): sin esto, renderizar las columnas
    # template/user en el listado admin dispara una query extra por fila.
    list_select_related = ('template', 'user')
    list_display  = ('template', 'user', 'channel', 'status', 'sent_at', 'created_at')
    list_filter   = ('channel', 'status')
    search_fields = ('user__email', 'template__slug')
    readonly_fields = (
        'uuid', 'user', 'template', 'channel', 'status',
        'sent_at', 'payload_context', 'error_message', 'created_at',
    )
    ordering = ('-created_at',)


@admin.register(MetaWebhookEvent)
class MetaWebhookEventAdmin(admin.ModelAdmin):
    """Solo lectura -- lo escribe el webhook (notifications/api/whatsapp_webhook.py)
    y la tarea process_whatsapp_inbound_task. FASE 6 integracion Meta Business."""
    list_display = (
        'received_at', 'object_type', 'event_type', 'status',
        'signature_valid', 'phone_number_id', 'external_message_id', 'error_code',
    )
    list_filter = ('object_type', 'status', 'signature_valid', 'event_type')
    search_fields = ('external_message_id', 'payload_hash', 'waba_id', 'phone_number_id')
    date_hierarchy = 'received_at'
    ordering = ('-received_at',)
    readonly_fields = (
        'uuid', 'object_type', 'event_type', 'business_id', 'waba_id',
        'phone_number_id', 'external_message_id', 'payload_hash', 'signature_valid',
        'status', 'received_at', 'processed_at', 'retry_count', 'error_code',
        'payload', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False
