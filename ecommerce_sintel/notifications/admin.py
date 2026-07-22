from django.contrib import admin
from notifications.models import NotificationTemplate, UserNotificationPreference, NotificationLog


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
    list_display  = ('template', 'user', 'channel', 'status', 'sent_at', 'created_at')
    list_filter   = ('channel', 'status')
    search_fields = ('user__email', 'template__slug')
    readonly_fields = (
        'uuid', 'user', 'template', 'channel', 'status',
        'sent_at', 'payload_context', 'error_message', 'created_at',
    )
    ordering = ('-created_at',)
