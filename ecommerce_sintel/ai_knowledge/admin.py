from django.contrib import admin

from ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument


class AIKnowledgeChunkInline(admin.TabularInline):
    model = AIKnowledgeChunk
    extra = 0
    fields = ('chunk_index', 'content', 'embedding_model', 'embedded_at')
    readonly_fields = ('embedding_model', 'embedded_at')


@admin.register(AIKnowledgeDocument)
class AIKnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'app_name', 'visibility', 'is_active', 'updated_at', 'updated_by')
    list_filter = ('visibility', 'is_active', 'language')
    search_fields = ('title', 'app_name', 'source')
    inlines = [AIKnowledgeChunkInline]
