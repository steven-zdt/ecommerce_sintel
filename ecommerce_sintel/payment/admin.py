from django.contrib import admin
from payment.models import Transaction, CodTransaction, NequiTransaction, TransactionEvent, PaymentFeatureFlags


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ('uuid', 'order', 'wompi_id', 'status', 'amount_in_cents', 'currency', 'created_at')
    list_filter   = ('status', 'currency')
    search_fields = ('wompi_id', 'order__uuid')
    readonly_fields = ('uuid', 'created_at', 'updated_at', 'integrity_signature')


@admin.register(CodTransaction)
class CodTransactionAdmin(admin.ModelAdmin):
    list_display  = ('uuid', 'order', 'status', 'delivered_at', 'created_at')
    list_filter   = ('status',)
    search_fields = ('order__uuid',)
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(NequiTransaction)
class NequiTransactionAdmin(admin.ModelAdmin):
    list_display  = ('uuid', 'order', 'phone_number', 'status', 'amount', 'created_at')
    list_filter   = ('status',)
    search_fields = ('phone_number', 'message_id', 'order__uuid')
    readonly_fields = ('uuid', 'created_at', 'updated_at', 'message_id')


@admin.register(TransactionEvent)
class TransactionEventAdmin(admin.ModelAdmin):
    """Solo lectura -- historial append-only (ADR-001 Fase 4), nunca se edita a mano."""
    list_display  = ('uuid', 'transaction', 'source', 'previous_status', 'new_status', 'processed', 'created_at')
    list_filter   = ('source', 'processed')
    search_fields = ('transaction__uuid', 'correlation_id', 'transaction__wompi_id')
    readonly_fields = [f.name for f in TransactionEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentFeatureFlags)
class PaymentFeatureFlagsAdmin(admin.ModelAdmin):
    """
    Toggle operativo (ADR-001 Fase 5): activar/desactivar card_api_flow_enabled
    aqui tiene efecto inmediato en el checkout, sin necesidad de desplegar
    codigo nuevo (el frontend lo consulta via GET payments/feature-flags/).
    """
    list_display   = ('id', 'card_api_flow_enabled', 'is_active', 'updated_at')
    readonly_fields = ('uuid', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        # ADR-001 Fase 8 (alertas operativas): mismo evento que el toggle del
        # panel Vue (dashboard/api/views.py) -- aqui tambien hay 'request',
        # asi que se audita quien lo cambio, no solo que cambio.
        previous_enabled = None
        if change:
            previous_enabled = PaymentFeatureFlags.objects.filter(pk=obj.pk).values_list(
                'card_api_flow_enabled', flat=True,
            ).first()

        super().save_model(request, obj, form, change)

        if change and previous_enabled is not None and previous_enabled != obj.card_api_flow_enabled:
            from security.models import SecurityEvent
            from security.services.commands import SecurityCommands
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED, request=request, user=request.user,
                severity=SecurityEvent.SEVERITY_WARNING,
                metadata={
                    'flag': 'card_api_flow_enabled',
                    'previous_value': previous_enabled,
                    'new_value': obj.card_api_flow_enabled,
                    'source': 'django_admin',
                },
            )
