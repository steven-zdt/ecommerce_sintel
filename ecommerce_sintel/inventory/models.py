import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from ecommerce.base_models import SintelBaseModel

class StockRecord(SintelBaseModel):
    """
    MASTER RECORD: Acts as the core anchor for any item that can be 
    sold, rented, or quoted in the Sintel platform.
    """
    # Dynamic link to ProductVariant, EquipmentVariant, or ServiceVariant.
    # object_id guarda el campo `uuid` de la variante (no su `pk` autoincremental) para no
    # depender del id interno -- por diseño, pero eso significa que item_variant NUNCA resuelve
    # nada (Django empareja GenericForeignKey contra `pk`, no contra `uuid`). No usar
    # obj.item_variant en codigo nuevo; usar StockRecordSelector.batch_load_item_variants()
    # o un .filter(uuid=object_id) manual sobre el content_type.model_class().
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField(db_index=True)
    item_variant = GenericForeignKey('content_type', 'object_id')
    
    sku = models.CharField(max_length=100, unique=True)  # unique=True automatically creates a unique index in Django
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # is_deleted ya lo aporta SintelBaseModel (con db_index=True) -- redeclararlo aqui sin
    # db_index pisaba silenciosamente el campo indexado del padre.

    class Meta:
        verbose_name = "registro de stock"
        verbose_name_plural = "registros de stock"
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id'],
                name='unique_stock_record_per_variant'
            )
        ]

    def __str__(self):
        return f"Stock: {self.sku} | Qty: {self.stock}"

        

class InventoryTransaction(SintelBaseModel):
    MOVEMENT_TYPES = (
        ('ENTRY', 'Entry (Purchase/Restock)'),
        ('EXIT', 'Exit (Sale/Adjustment)'),
        ('RESERVE', 'Reserve (Quote)'),
    )

    stock_record = models.ForeignKey(
        StockRecord, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        null=True, blank=True # Nullable for legacy support if needed
    )
    
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField()
    balance_after = models.IntegerField(help_text="Stock level after this transaction")
    reference = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='quantity_must_be_greater_than_zero'
            )
        ]

    def __str__(self):
        return f"{self.movement_type} | {self.stock_record.sku} | Qty: {self.quantity}"
