# Shim de compatibilidad — implementación movida a wompi/online/api/serializers.py
from payment.online.api.serializers import TransactionSerializer  # noqa: F401

__all__ = ['TransactionSerializer']
