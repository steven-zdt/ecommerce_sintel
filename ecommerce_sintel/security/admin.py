from django.contrib import admin
from security.models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'event_type', 'severity', 'user', 'ip_address', 'path', 'created_at')
    list_filter = ('event_type', 'severity')
    search_fields = ('user__email', 'ip_address', 'path')
    raw_id_fields = ('user',)
    readonly_fields = (
        'event_type', 'severity', 'user', 'ip_address', 'user_agent', 'path',
        'metadata', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
