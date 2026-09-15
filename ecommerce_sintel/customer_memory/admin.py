"""customer_memory/admin.py -- FASE 9, Mision RAG-POST2.

Auditable/deletable/revisable (regla de la mision, FASE 9): Django Admin es
el mecanismo real hoy -- no se construyo un panel dedicado en /panel/soporte
en esta fase (fuera del alcance explicito de la mision, mismo criterio que
F-10 de la mision anterior: se documenta como pendiente, no se inventa un
CRUD nuevo sin que se pida). Ver AUDITORIA/RAG_POST2_FINAL_CERTIFICATION.md."""
from django.contrib import admin

from .models import CustomerMemoryRecord


@admin.register(CustomerMemoryRecord)
class CustomerMemoryRecordAdmin(admin.ModelAdmin):
    list_display = ('customer', 'category', 'content', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'is_deleted')
    search_fields = ('customer__email', 'content')
    readonly_fields = ('uuid', 'source_conversation_id', 'created_at', 'updated_at')
