from django.contrib import admin

from ai_provider.models import AIChannelConfig, AIChannelFallback, AIModel, AIProvider


class AIModelInline(admin.TabularInline):
    model = AIModel
    extra = 0
    fields = ('model_id', 'display_name', 'is_active', 'is_default', 'discovered_automatically', 'temperature', 'max_tokens')


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'is_active', 'is_default', 'display_order', 'last_tested_at', 'last_test_ok')
    list_filter = ('kind', 'is_active', 'is_default')
    search_fields = ('name', 'slug', 'base_url')
    readonly_fields = ('slug', 'last_tested_at', 'last_test_ok', 'last_test_latency_ms', 'last_test_error')
    inlines = [AIModelInline]


class AIChannelFallbackInline(admin.TabularInline):
    model = AIChannelFallback
    extra = 0
    fields = ('model', 'order')


@admin.register(AIChannelConfig)
class AIChannelConfigAdmin(admin.ModelAdmin):
    list_display = ('channel', 'enabled', 'primary_model', 'updated_by', 'updated_at')
    list_filter = ('enabled',)
    inlines = [AIChannelFallbackInline]
