from rest_framework import serializers
from security.models import SecurityEvent


class SecurityEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, default=None)

    class Meta:
        model = SecurityEvent
        fields = (
            'uuid', 'event_type', 'severity', 'user_email', 'ip_address',
            'user_agent', 'path', 'metadata', 'created_at',
        )
