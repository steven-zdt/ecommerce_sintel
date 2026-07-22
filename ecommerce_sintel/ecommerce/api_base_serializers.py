from rest_framework import serializers

class BaseWriteSerializer(serializers.ModelSerializer):
    """
    Base serializer for write operations (Create/Update).
    Standardizes validation of unknown fields and common write logic.
    """
    def validate(self, data):
        # Add custom global write validation here if needed
        return data

class BaseModelSerializerV1(serializers.ModelSerializer):
    """
    Base serializer for read operations.
    Includes common fields like uuid and timestamps by default.
    """
    class Meta:
        fields = ('uuid', 'inserted_at', 'updated_at')
        read_only_fields = ('uuid', 'inserted_at', 'updated_at')
