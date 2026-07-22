import logging
from django.db import transaction
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from inventory.models import InventoryTransaction, StockRecord
from inventory.services.kardex import InventoryKardex
from inventory.services.dtos import StockAdjustmentDTO, InventoryTransactionResultDTO

logger = logging.getLogger(__name__)

class InventoryCommands:
    @staticmethod
    @transaction.atomic
    def register_entry(dto: StockAdjustmentDTO) -> InventoryTransactionResultDTO:
        """
        Register a stock entry (purchase/restock).
        Params: dto (StockAdjustmentDTO)
        Returns: InventoryTransactionResultDTO
        """
        stock_record = StockRecord.objects.select_for_update().get(uuid=dto.stock_record_uuid)

        current = stock_record.stock
        new_balance = InventoryKardex.calculate_new_balance(current, 'ENTRY', dto.quantity)
        
        # Update the denormalized stock field on StockRecord
        stock_record.stock = new_balance
        stock_record.save(update_fields=['stock', 'updated_at'])
        
        reference = dto.reference or ""
        tx = InventoryTransaction.objects.create(
            stock_record=stock_record,
            movement_type='ENTRY',
            quantity=dto.quantity,
            balance_after=new_balance,
            reference=reference,
        )
        
        # Cache optimization: update the cache on transaction commit
        cache_key = f"stock_record_balance_{stock_record.id}"
        transaction.on_commit(lambda ck=cache_key, nb=new_balance: cache.set(ck, nb, timeout=300))
        
        logger.info("[inventory:register_entry] SKU=%s qty=%s new_balance=%s", stock_record.sku, dto.quantity, new_balance)
        
        return InventoryTransactionResultDTO(
            id=tx.id,
            uuid=tx.uuid,
            stock_record_uuid=stock_record.uuid,
            sku=stock_record.sku,
            movement_type=tx.movement_type,
            quantity=tx.quantity,
            balance_after=tx.balance_after,
            reference=tx.reference,
            created_at=tx.created_at,
        )

    @staticmethod
    @transaction.atomic
    def create_stock_record(
        app_label: str,
        model_name: str,
        variant_uuid,
        sku: str,
        initial_stock: int = 0,
    ) -> StockRecord:
        """
        Create a StockRecord for a ProductVariant, ServiceVariant or EquipmentVariant.
        Raises ValueError on duplicate content-type/variant or duplicate SKU.
        If initial_stock > 0, registers an entry transaction atomically.
        """
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            raise ValueError('Tipo de variante no valido.')

        if StockRecord.objects.filter(content_type=content_type, object_id=variant_uuid).exists():
            raise ValueError('Ya existe un registro de stock para esta variante.')

        if StockRecord.objects.filter(sku=sku).exists():
            raise ValueError(f'El SKU "{sku}" ya esta en uso.')

        stock_record = StockRecord.objects.create(
            content_type=content_type,
            object_id=variant_uuid,
            sku=sku,
            stock=0,
            is_active=True,
        )

        if initial_stock > 0:
            dto = StockAdjustmentDTO(
                stock_record_uuid=stock_record.uuid,
                quantity=initial_stock,
                reference='Stock inicial',
            )
            InventoryCommands.register_entry(dto)
            stock_record.refresh_from_db()

        logger.info('[inventory:create_stock_record] SKU=%s variant=%s', sku, variant_uuid)
        return stock_record

    @staticmethod
    @transaction.atomic
    def register_exit(dto: StockAdjustmentDTO) -> InventoryTransactionResultDTO:
        """
        Register a stock exit (sale/adjustment).
        Params: dto (StockAdjustmentDTO)
        Returns: InventoryTransactionResultDTO
        Raises: ValidationError if stock insufficient
        """
        stock_record = StockRecord.objects.select_for_update().get(uuid=dto.stock_record_uuid)

        current = stock_record.stock
        InventoryKardex.validate_stock_availability(current, dto.quantity)
        new_balance = InventoryKardex.calculate_new_balance(current, 'EXIT', dto.quantity)
        
        # Update the denormalized stock field on StockRecord
        stock_record.stock = new_balance
        stock_record.save(update_fields=['stock', 'updated_at'])
        
        reference = dto.reference or ""
        tx = InventoryTransaction.objects.create(
            stock_record=stock_record,
            movement_type='EXIT',
            quantity=dto.quantity,
            balance_after=new_balance,
            reference=reference,
        )
        
        # Cache optimization: update the cache on transaction commit
        cache_key = f"stock_record_balance_{stock_record.id}"
        transaction.on_commit(lambda ck=cache_key, nb=new_balance: cache.set(ck, nb, timeout=300))
        
        logger.info("[inventory:register_exit] SKU=%s qty=%s new_balance=%s", stock_record.sku, dto.quantity, new_balance)
        
        return InventoryTransactionResultDTO(
            id=tx.id,
            uuid=tx.uuid,
            stock_record_uuid=stock_record.uuid,
            sku=stock_record.sku,
            movement_type=tx.movement_type,
            quantity=tx.quantity,
            balance_after=tx.balance_after,
            reference=tx.reference,
            created_at=tx.created_at,
        )
