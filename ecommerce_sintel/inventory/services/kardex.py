from django.core.exceptions import ValidationError

class InsufficientStockError(ValidationError):
    """Exception raised when there is not enough stock for an exit movement."""
    pass

class InventoryKardex:
    """Mathematical logic for stock calculation (pure functions)"""
    
    @staticmethod
    def calculate_new_balance(current_balance: int, movement_type: str, quantity: int) -> int:
        if movement_type == 'ENTRY':
            return current_balance + quantity
        elif movement_type == 'EXIT':
            return current_balance - quantity
        raise ValueError("Invalid movement type")

    @staticmethod
    def validate_stock_availability(current_balance: int, requested_quantity: int) -> None:
        if current_balance < requested_quantity:
            raise InsufficientStockError(
                f"Insufficient stock. Available: {current_balance}, Requested: {requested_quantity}"
            )

