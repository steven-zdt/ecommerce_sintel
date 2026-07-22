from dataclasses import dataclass
from datetime import datetime
import uuid
from typing import Optional

@dataclass(frozen=True)
class StockAdjustmentDTO:
    """
    Input DTO representing a request to adjust stock (either ENTRY or EXIT).
    """
    stock_record_uuid: uuid.UUID
    quantity: int
    reference: Optional[str] = None

@dataclass(frozen=True)
class InventoryTransactionResultDTO:
    """
    Output DTO representing the result of an inventory transaction.
    """
    id: int
    uuid: uuid.UUID
    stock_record_uuid: uuid.UUID
    sku: str
    movement_type: str
    quantity: int
    balance_after: int
    reference: Optional[str]
    created_at: datetime
