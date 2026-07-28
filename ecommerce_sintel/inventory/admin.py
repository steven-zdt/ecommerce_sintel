"""S-05 (auditoria enterprise): inventory/ no tenia ningun admin.py -- el
kardex de stock (fuente de verdad de disponibilidad) no era inspeccionable
desde /admin/. Nota: StockRecord.item_variant (GenericForeignKey) nunca
resuelve (object_id guarda uuid, no pk -- ver comentario en models.py), asi
que list_display usa content_type/object_id directos, no item_variant."""
from django.contrib import admin

from inventory.models import StockRecord, InventoryTransaction


class InventoryTransactionInline(admin.TabularInline):
    model = InventoryTransaction
    extra = 0
    readonly_fields = ('movement_type', 'quantity', 'balance_after', 'reference', 'created_at')
    can_delete = False
    ordering = ('-created_at',)


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ('sku', 'content_type', 'object_id', 'stock', 'is_active', 'created_at')
    list_filter = ('is_active', 'content_type')
    search_fields = ('sku',)
    inlines = [InventoryTransactionInline]


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    # Append-only (ver inventory/CLAUDE.md): nunca editar/borrar registros existentes.
    list_display = ('stock_record', 'movement_type', 'quantity', 'balance_after', 'created_at')
    list_select_related = ('stock_record',)
    list_filter = ('movement_type',)
    search_fields = ('stock_record__sku', 'reference')
    readonly_fields = [f.name for f in InventoryTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
