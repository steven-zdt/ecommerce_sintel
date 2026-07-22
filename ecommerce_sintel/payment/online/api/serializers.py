from rest_framework import serializers
from payment.models import Transaction, TransactionEvent


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            'id', 'uuid', 'wompi_id', 'amount_in_cents',
            'currency', 'status', 'created_at',
            # Agregados para el panel admin (Fase 3 auditoria enterprise_sync 2026-07-11):
            # aditivo, no quita ni renombra campos existentes.
            'order', 'rental_request', 'payment_method_type',
            # ADR-001 Fase 7 (panel admin con acciones reales): trazabilidad visible.
            'correlation_id',
        )


class TransactionEventSerializer(serializers.ModelSerializer):
    """ADR-001 Fase 7: historial append-only visible desde el panel admin."""
    class Meta:
        model = TransactionEvent
        fields = (
            'uuid', 'source', 'previous_status', 'new_status',
            'correlation_id', 'processed', 'error_detail', 'created_at',
        )
