from django.contrib import admin
from support.models import ChatRoom, ChatMessage, ChatRoomContext, SupportTicket


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


@admin.register(ChatRoomContext)
class ChatRoomContextAdmin(admin.ModelAdmin):
    # D-05 (auditoria enterprise): ChatRoom/ChatMessage ya estaban
    # registrados con ModelAdmin propio; ChatRoomContext (el vinculo a
    # Order/RentalRequest) no lo estaba.
    list_display = ('room', 'context_type', 'order', 'rental_request', 'created_at')
    list_filter = ('context_type',)
    raw_id_fields = ('room', 'order', 'rental_request')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'status', 'priority', 'category', 'assigned_admin', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('ticket_number', 'subject', 'chat_room__user__email', 'contact_phone', 'contact_email')
    raw_id_fields = ('chat_room', 'assigned_admin')
