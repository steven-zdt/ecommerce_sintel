"""
Django Admin Configuration for Technical Services Module.

Provides admin interface for all technical service models with appropriate
filters, search fields, and read-only configurations.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ServiceCategory,
    ServiceLevel,
    ServiceConfiguration,
    TechnicalService,
    ServiceVariant,
    ServiceMaterial,
    ServiceImage,
    ServiceReview,
    OrderServiceDetail,
    OrderServiceTimeline,
    ServiceAttachment,
    ServicePriceHistory,
    ServiceBooking,
    ServiceCostRule,
    ServiceCostAssignment,
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'service_count', 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('slug', 'uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('General', {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def service_count(self, obj):
        count = obj.services.filter(is_deleted=False).count()
        return format_html(
            '<span style="background:#e0e7ff;padding:2px 8px;border-radius:4px;font-size:12px">{} services</span>',
            count
        )
    service_count.short_description = 'Services'


@admin.register(ServiceLevel)
class ServiceLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_count', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('slug', 'uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('General', {
            'fields': ('name', 'slug')
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def service_count(self, obj):
        count = obj.services.filter(is_deleted=False).count()
        return format_html(
            '<span style="background:#f0fdf4;padding:2px 8px;border-radius:4px;font-size:12px">{} services</span>',
            count
        )
    service_count.short_description = 'Services'


@admin.register(ServiceConfiguration)
class ServiceConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'smlv_display', 'iva_rate_display', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('General', {
            'fields': ('name', 'is_active')
        }),
        ('Labor Costs (SMLV Colombia)', {
            'fields': ('smlv', 'transport_subsidy', 'benefit_rate', 'indirect_costs_rate')
        }),
        ('Taxation', {
            'fields': ('iva_rate',)
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def smlv_display(self, obj):
        return f"${obj.smlv:,.0f}"
    smlv_display.short_description = 'SMLV'

    def iva_rate_display(self, obj):
        return f"{obj.iva_rate}%"
    iva_rate_display.short_description = 'IVA'


@admin.register(TechnicalService)
class TechnicalServiceAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'level',
        'variant_count',
        'status_badge',
        'vendor_display',
        'created_at'
    )
    search_fields = ('name', 'slug', 'description')
    list_filter = (
        'is_active',
        'is_featured',
        'is_purchasable',
        'category',
        'level',
        'created_at'
    )
    readonly_fields = ('slug', 'uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('General', {
            'fields': ('name', 'slug', 'vendor', 'description')
        }),
        ('Classification', {
            'fields': ('category', 'level')
        }),
        ('Visibility & Status', {
            'fields': ('is_active', 'is_featured', 'is_purchasable')
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def variant_count(self, obj):
        count = obj.variants.filter(is_deleted=False).count()
        return format_html(
            '<span style="background:#fef3c7;padding:2px 8px;border-radius:4px;font-size:12px">{} variants</span>',
            count
        )
    variant_count.short_description = 'Variants'

    def status_badge(self, obj):
        if not obj.is_active:
            return format_html('<span style="color:#dc2626">Inactive</span>')
        elif obj.is_featured:
            return format_html('<span style="color:#2563eb">Featured</span>')
        return format_html('<span style="color:#16a34a">Active</span>')
    status_badge.short_description = 'Status'

    def vendor_display(self, obj):
        return obj.vendor.username if obj.vendor else '—'
    vendor_display.short_description = 'Vendor'


@admin.register(ServiceVariant)
class ServiceVariantAdmin(admin.ModelAdmin):
    list_display = (
        'sku',
        'service_link',
        'pricing_strategy',
        'price_display',
        'is_default_badge',
        'is_active_badge',
        'created_at'
    )
    search_fields = ('sku', 'service__name')
    list_filter = (
        'pricing_strategy',
        'is_active',
        'is_default',
        'service__category',
        'created_at'
    )
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('Service Link', {
            'fields': ('service', 'sku')
        }),
        ('Pricing Strategy', {
            'fields': ('pricing_strategy', 'estimated_hours', 'complexity_factor', 'fixed_price')
        }),
        ('Duration Constraints', {
            'fields': ('min_duration', 'max_duration'),
            'classes': ('collapse',)
        }),
        ('Capacity Management', {
            'fields': ('simultaneous_capacity',)
        }),
        ('Status', {
            'fields': ('is_default', 'is_active')
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def service_link(self, obj):
        return f"{obj.service.name}"
    service_link.short_description = 'Service'

    def price_display(self, obj):
        if obj.pricing_strategy == 'FIXED':
            return f"${obj.fixed_price:,.0f}" if obj.fixed_price else "—"
        return f"{obj.estimated_hours}h × {obj.complexity_factor}x ({obj.pricing_strategy})"
    price_display.short_description = 'Price'

    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html('<span style="background:#dcfce7;color:#16a34a;padding:2px 8px;border-radius:4px;font-size:11px">DEFAULT</span>')
        return "—"
    is_default_badge.short_description = 'Default'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#dbeafe;color:#0284c7;padding:2px 8px;border-radius:4px;font-size:11px">ACTIVE</span>')
        return format_html('<span style="background:#fee2e2;color:#dc2626;padding:2px 8px;border-radius:4px;font-size:11px">INACTIVE</span>')
    is_active_badge.short_description = 'Status'


class ServiceMaterialInline(admin.TabularInline):
    model = ServiceMaterial
    extra = 1
    fields = ('product_variant', 'quantity')
    readonly_fields = ('created_at',)


@admin.register(ServiceMaterial)
class ServiceMaterialAdmin(admin.ModelAdmin):
    list_display = ('product_display', 'variant_display', 'quantity', 'created_at')
    search_fields = ('product_variant__sku', 'variant__sku')
    list_filter = ('created_at', 'variant__service')
    readonly_fields = ('uuid', 'created_at', 'updated_at')

    def product_display(self, obj):
        return f"{obj.product_variant.sku}" if obj.product_variant else "—"
    product_display.short_description = 'Product'

    def variant_display(self, obj):
        return f"{obj.variant.sku}" if obj.variant else "—"
    variant_display.short_description = 'Variant'


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'service_display', 'variant_display', 'is_primary', 'created_at')
    search_fields = ('service__name', 'variant__sku', 'alt_text')
    list_filter = ('is_primary', 'created_at', 'service')
    readonly_fields = ('uuid', 'created_at', 'updated_at', 'image_preview')

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:4px">',
                obj.image.url
            )
        return "—"
    thumbnail.short_description = 'Image'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:300px;max-height:200px;border-radius:4px">',
                obj.image.url
            )
        return "No image"

    def service_display(self, obj):
        return obj.service.name if obj.service else "—"
    service_display.short_description = 'Service'

    def variant_display(self, obj):
        return obj.variant.sku if obj.variant else "—"
    variant_display.short_description = 'Variant'


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ('service_display', 'rating_stars', 'user_display', 'comment_preview', 'created_at')
    search_fields = ('service__name', 'user__username', 'comment')
    list_filter = ('rating', 'created_at', 'service')
    readonly_fields = ('uuid', 'created_at', 'updated_at')

    def service_display(self, obj):
        return obj.service.name
    service_display.short_description = 'Service'

    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = 'Reviewer'

    def rating_stars(self, obj):
        stars = "⭐" * obj.rating
        return format_html('<span style="font-size:14px">{}</span>', stars)
    rating_stars.short_description = 'Rating'

    def comment_preview(self, obj):
        preview = obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return preview
    comment_preview.short_description = 'Comment'


@admin.register(ServicePriceHistory)
class ServicePriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'variant_display',
        'old_price_display',
        'new_price_display',
        'price_change_badge',
        'changed_by_display',
        'created_at'
    )
    search_fields = ('variant__sku', 'changed_by__username')
    list_filter = ('created_at', 'variant__service')
    readonly_fields = ('variant', 'old_price', 'new_price', 'changed_by', 'created_at', 'uuid')
    date_hierarchy = 'created_at'

    def variant_display(self, obj):
        return obj.variant.sku if obj.variant else "—"
    variant_display.short_description = 'Variant'

    def old_price_display(self, obj):
        return f"${obj.old_price:,.0f}" if obj.old_price else "N/A"
    old_price_display.short_description = 'Old Price'

    def new_price_display(self, obj):
        return f"${obj.new_price:,.0f}" if obj.new_price else "N/A"
    new_price_display.short_description = 'New Price'

    def price_change_badge(self, obj):
        if obj.old_price and obj.new_price:
            change = obj.new_price - obj.old_price
            percent = (change / obj.old_price * 100) if obj.old_price else 0
            color = '#16a34a' if change >= 0 else '#dc2626'
            symbol = '↑' if change >= 0 else '↓'
            return format_html(
                '<span style="background:{}20;color:{};padding:4px 8px;border-radius:4px;font-size:11px">{} ${:,.0f} ({:.0f}%)</span>',
                color, color, symbol, abs(change), abs(percent)
            )
        return "—"
    price_change_badge.short_description = 'Change'

    def changed_by_display(self, obj):
        return obj.changed_by.username if obj.changed_by else "System"
    changed_by_display.short_description = 'Changed By'


@admin.register(OrderServiceDetail)
class OrderServiceDetailAdmin(admin.ModelAdmin):
    list_display = (
        'order_display',
        'priority_badge',
        'status_badge',
        'scheduled_display',
        'technician_display',
        'created_at'
    )
    search_fields = ('order__id', 'technician__email', 'address')
    list_filter = ('priority', 'created_at')
    readonly_fields = (
        'order', 'uuid', 'created_at', 'updated_at',
        'professional_type_snapshot', 'applied_rate_type', 'applied_rate_amount',
        # Plan "Migracion a autoridad unica de tecnico" FASE 1 (2026-08-14) --
        # `technician` es legacy/compatibility, NO fuente de verdad
        # (ServiceOperation.technician lo es). Este ModelAdmin permitia
        # editar el campo directo, sin pasar por ServiceAssignmentCommands:
        # sin validar disponibilidad, sin liberar al tecnico anterior, sin
        # timeline, sin notificacion -- via de escritura sin auditoria
        # detectada en TECHNICIAN_ASSIGNMENT_MIGRATION_FASE0_2026-08-14.md.
        # Se cierra aqui; la asignacion real debe hacerse siempre desde
        # /panel/servicios (ServiceOperation), nunca desde /admin/.
        'technician',
    )

    def order_display(self, obj):
        return f"Order #{obj.order.id}"
    order_display.short_description = 'Order'

    def priority_badge(self, obj):
        colors = {'low': '#6b7280', 'medium': '#2563eb', 'high': '#f59e0b', 'critical': '#dc2626'}
        color = colors.get(obj.priority, '#6b7280')
        return format_html(
            '<span style="background:{}20;color:{};padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            color, color, obj.priority.upper()
        )
    priority_badge.short_description = 'Priority'

    def status_badge(self, obj):
        timeline = obj.order_service_timeline.order_by('-created_at').first()
        status = timeline.status if timeline else 'pending'
        return status.upper()
    status_badge.short_description = 'Status'

    def scheduled_display(self, obj):
        if obj.scheduled_at:
            return obj.scheduled_at.strftime('%Y-%m-%d %H:%M')
        return "—"
    scheduled_display.short_description = 'Scheduled'

    def technician_display(self, obj):
        # FASE 9 (2026-08-14): usa el selector sancionado en vez del snapshot
        # legacy directo -- ver ARQUITECTURA_COMPLETA_SERVICES.md #23.
        from technical_services.services.selectors import ServiceTechnicianReconciliationSelector
        technician = ServiceTechnicianReconciliationSelector.get_assigned_technician(obj.order)
        if technician:
            return technician.username
        return "Unassigned"
    technician_display.short_description = 'Technician'


@admin.register(OrderServiceTimeline)
class OrderServiceTimelineAdmin(admin.ModelAdmin):
    list_display = ('order_display', 'status_badge', 'created_by_display', 'notes_preview', 'created_at')
    search_fields = ('order__id', 'status', 'notes')
    list_filter = ('status', 'created_at')
    readonly_fields = ('order', 'uuid', 'created_at')
    date_hierarchy = 'created_at'

    def order_display(self, obj):
        return f"Order #{obj.order.id}"
    order_display.short_description = 'Order'

    def status_badge(self, obj):
        colors = {'pending': '#gray', 'assigned': '#2563eb', 'in_progress': '#f59e0b', 'completed': '#16a34a', 'cancelled': '#dc2626'}
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}20;color:{};padding:2px 6px;border-radius:4px;font-size:11px">{}</span>',
            color, color, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def created_by_display(self, obj):
        return obj.created_by.username if obj.created_by else "System"
    created_by_display.short_description = 'By'

    def notes_preview(self, obj):
        preview = obj.notes[:60] + "..." if len(obj.notes) > 60 else obj.notes
        return preview
    notes_preview.short_description = 'Notes'


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        'variant_display',
        'time_range_display',
        'status_badge',
        'capacity_display',
        'created_at'
    )
    search_fields = ('service_variant__sku', 'order_service_detail__order__id')
    list_filter = ('status', 'created_at', 'service_variant')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def variant_display(self, obj):
        return obj.service_variant.sku if obj.service_variant else "—"
    variant_display.short_description = 'Variant'

    def time_range_display(self, obj):
        return f"{obj.start_time.strftime('%Y-%m-%d %H:%M')} → {obj.end_time.strftime('%H:%M')}"
    time_range_display.short_description = 'Time Range'

    def status_badge(self, obj):
        colors = {'scheduled': '#2563eb', 'active': '#16a34a', 'completed': '#9ca3af', 'cancelled': '#dc2626'}
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}20;color:{};padding:2px 6px;border-radius:4px;font-size:11px">{}</span>',
            color, color, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def capacity_display(self, obj):
        if obj.service_variant:
            return obj.service_variant.simultaneous_capacity
        return "—"
    capacity_display.short_description = 'Capacity'


@admin.register(ServiceAttachment)
class ServiceAttachmentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'doc_type', 'file_size_display', 'uploaded_by_display', 'created_at')
    search_fields = ('file_name', 'uploaded_by__username')
    list_filter = ('doc_type', 'created_at')
    readonly_fields = ('uuid', 'created_at', 'updated_at')

    def file_size_display(self, obj):
        size_kb = obj.file_size / 1024 if obj.file_size else 0
        return f"{size_kb:.1f} KB"
    file_size_display.short_description = 'Size'

    def uploaded_by_display(self, obj):
        return obj.uploaded_by.username if obj.uploaded_by else "—"
    uploaded_by_display.short_description = 'Uploaded By'


@admin.register(ServiceCostRule)
class ServiceCostRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'cost_type_badge',
        'context_badge',
        'value_display',
        'global_badge',
        'is_active_badge',
        'created_at'
    )
    search_fields = ('name', 'description')
    list_filter = ('cost_type', 'context', 'applies_globally', 'is_active', 'created_at')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('General', {
            'fields': ('name', 'description')
        }),
        ('Rule Configuration', {
            'fields': ('cost_type', 'value', 'context')
        }),
        ('Scope', {
            'fields': ('applies_globally', 'is_active')
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def cost_type_badge(self, obj):
        colors = {'FIXED': '#2563eb', 'PERCENTAGE': '#f59e0b'}
        color = colors.get(obj.cost_type, '#6b7280')
        return format_html(
            '<span style="background:{}20;color:{};padding:2px 6px;border-radius:4px;font-size:11px">{}</span>',
            color, color, obj.cost_type
        )
    cost_type_badge.short_description = 'Type'

    def context_badge(self, obj):
        colors = {'TAX': '#dc2626', 'DISCOUNT': '#16a34a', 'SETUP': '#2563eb', 'OPERATIONAL': '#f59e0b'}
        color = colors.get(obj.context, '#6b7280')
        return format_html(
            '<span style="background:{}20;color:{};padding:2px 6px;border-radius:4px;font-size:11px">{}</span>',
            color, color, obj.context
        )
    context_badge.short_description = 'Context'

    def value_display(self, obj):
        if obj.cost_type == 'FIXED':
            return f"${obj.value:,.0f}"
        return f"{obj.value}%"
    value_display.short_description = 'Value'

    def global_badge(self, obj):
        if obj.applies_globally:
            return format_html('<span style="color:#16a34a;font-weight:600">GLOBAL</span>')
        return format_html('<span style="color:#9ca3af">Variant-specific</span>')
    global_badge.short_description = 'Scope'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#dcfce7;color:#16a34a;padding:2px 8px;border-radius:4px;font-size:11px">ACTIVE</span>')
        return format_html('<span style="background:#fee2e2;color:#dc2626;padding:2px 8px;border-radius:4px;font-size:11px">INACTIVE</span>')
    is_active_badge.short_description = 'Status'


@admin.register(ServiceCostAssignment)
class ServiceCostAssignmentAdmin(admin.ModelAdmin):
    list_display = ('rule_display', 'variant_display', 'created_at')
    search_fields = ('rule__name', 'variant__sku')
    list_filter = ('created_at', 'rule__context')
    readonly_fields = ('uuid', 'created_at')

    def rule_display(self, obj):
        return obj.rule.name if obj.rule else "—"
    rule_display.short_description = 'Rule'

    def variant_display(self, obj):
        return obj.variant.sku if obj.variant else "—"
    variant_display.short_description = 'Variant'
