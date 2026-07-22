from rest_framework import serializers
from payment.models import NequiTransaction


class NequiInitializeSerializer(serializers.Serializer):
    order_uuid   = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=20)


class NequiTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model            = NequiTransaction
        fields           = ['uuid', 'order', 'phone_number', 'amount', 'status', 'created_at']
        read_only_fields = fields
