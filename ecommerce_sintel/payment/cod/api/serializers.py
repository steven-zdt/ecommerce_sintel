from rest_framework import serializers
from payment.models import CodTransaction


class CodTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodTransaction
        fields = ['uuid', 'order', 'status', 'delivered_at', 'notes', 'created_at']
        read_only_fields = fields
