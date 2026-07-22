# Re-exports de compatibilidad — no agregar lógica aquí.
# Implementaciones en módulos independientes:
#   wompi/shared/commands.py           → confirm_order_payment, _deduct_inventory_for_order
#   wompi/online/services/commands.py  → WompiCommands, PaymentCommands
#   wompi/cod/services/commands.py     → CodCommands
#   wompi/nequi/services/commands.py   → NequiCommands
from payment.shared.commands import confirm_order_payment, _deduct_inventory_for_order  # noqa: F401
from payment.online.services.commands import WompiCommands, PaymentCommands             # noqa: F401
from payment.cod.services.commands import CodCommands                                   # noqa: F401

__all__ = [
    'confirm_order_payment',
    '_deduct_inventory_for_order',
    'WompiCommands',
    'PaymentCommands',
    'CodCommands',
]
