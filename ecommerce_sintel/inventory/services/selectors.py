from django.db.models import QuerySet
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from inventory.models import InventoryTransaction, StockRecord

class StockRecordSelector:
    LIST_FIELDS = ('id', 'uuid', 'sku', 'stock', 'is_active', 'created_at')
    DETAIL_FIELDS = LIST_FIELDS + ('content_type', 'object_id')

    @staticmethod
    def list_all_active() -> QuerySet[StockRecord]:
        """Returns all active stock records optimized."""
        return StockRecord.objects.filter(is_active=True).select_related('content_type')

    @staticmethod
    def list_all_for_admin() -> QuerySet[StockRecord]:
        """Returns all stock records (including inactive) optimized."""
        return StockRecord.objects.all().select_related('content_type')

    @staticmethod
    def batch_load_item_variants(stock_records) -> dict:
        """
        Resuelve en bloque el "GenericForeignKey" item_variant de una lista de
        StockRecord: 1 query por content_type distinto (maximo 3: Product/Service/
        EquipmentVariant), en vez de 1 query por registro.

        NOTA: StockRecord.object_id guarda el campo `uuid` de la variante, NO su
        `pk` (id autoincremental) -- por eso `item_variant` (GenericForeignKey de
        Django) nunca resuelve nada por si solo (Django empareja object_id contra
        pk). GenericPrefetch tampoco sirve por la misma razon. Este metodo hace el
        join manual por uuid.

        Retorna {(content_type_id, object_id): variant_instance}.
        """
        from collections import defaultdict
        ids_by_content_type = defaultdict(set)
        for sr in stock_records:
            ids_by_content_type[sr.content_type_id].add(sr.object_id)

        result = {}
        for content_type_id, object_ids in ids_by_content_type.items():
            ct = ContentType.objects.get_for_id(content_type_id)
            model_class = ct.model_class()
            if model_class is None:
                continue
            for variant in model_class.objects.filter(uuid__in=object_ids):
                result[(content_type_id, variant.uuid)] = variant
        return result

    @staticmethod
    def get_by_uuid(uuid: str) -> StockRecord:
        return StockRecord.objects.get(uuid=uuid)

class InventorySelector:
    LIST_FIELDS = ('id', 'uuid', 'stock_record_id', 'movement_type', 'quantity', 'balance_after', 'reference', 'created_at')

    @staticmethod
    def get_current_stock(stock_record_id) -> int:
        """Returns the last balance_after for a StockRecord or 0 if no transactions exist. Uses caching.
        Also supports passing a variant instance directly to query its stock record.
        """
        if stock_record_id is not None and not isinstance(stock_record_id, int):
            return InventorySelector.get_stock_for_variant(stock_record_id)

        cache_key = f"stock_record_balance_{stock_record_id}"
        balance = cache.get(cache_key)
        if balance is not None:
            return balance
        
        last_tx = (
            InventoryTransaction.objects
            .filter(stock_record_id=stock_record_id)
            .only('balance_after')
            .order_by('-created_at')
            .first()
        )
        balance = last_tx.balance_after if last_tx else 0
        cache.set(cache_key, balance, timeout=300) # Cache for 5 minutes
        return balance

    @staticmethod
    def get_stock_for_variant(variant) -> int:
        """Returns current stock for any variant type via StockRecord. Returns 0 if no record exists."""
        from django.contrib.contenttypes.models import ContentType
        try:
            ct = ContentType.objects.get_for_model(type(variant))
            record = StockRecord.objects.filter(
                content_type=ct, object_id=variant.uuid, is_active=True
            ).first()
            if record is None:
                return 0
            return InventorySelector.get_current_stock(record.id)
        except Exception:
            return 0

    @staticmethod
    def list_movements(stock_record_id: int) -> QuerySet[InventoryTransaction]:
        """Returns all movements for a StockRecord optimized with only()."""
        return (
            InventoryTransaction.objects
            .filter(stock_record_id=stock_record_id)
            .only(*InventorySelector.LIST_FIELDS)
            .order_by('-created_at')
        )
