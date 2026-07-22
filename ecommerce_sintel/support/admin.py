from django.contrib import admin
from support.models import ChatRoom, ChatMessage


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user', 'status', 'assigned_admin', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email',)
    raw_id_fields = ('user', 'assigned_admin')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'room', 'sender', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__email', 'message')
    raw_id_fields = ('room', 'sender')
