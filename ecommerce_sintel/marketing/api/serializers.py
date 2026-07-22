from rest_framework import serializers
from marketing.models import (
    MarketingCampaign, FlashOffer, PersonalOffer, 
    CampaignLog, AgentRun
)

class CampaignLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignLog
        fields = ['uuid', 'channel', 'recipient', 'is_sent', 'sent_at', 'error_message']

class MarketingCampaignSerializer(serializers.ModelSerializer):
    logs = CampaignLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = MarketingCampaign
        fields = [
            'id', 'uuid', 'title', 'content', 'channels', 
            'scheduled_at', 'sent_at', 'is_completed', 'logs', 'created_at'
        ]

class FlashOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashOffer
        fields = [
            'id', 'uuid', 'name', 'description', 'discount_percentage',
            'start_time', 'end_time', 'is_active', 'created_at'
        ]

class AgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRun
        fields = [
            'id', 'uuid', 'triggered_by', 'status', 'llm_provider', 
            'llm_decision', 'campaign', 'created_at'
        ]

class ConsolidatedDashboardSerializer(serializers.Serializer):
    platform_overview = serializers.DictField()
    shop = serializers.DictField()
    renting = serializers.DictField()
    technical_services = serializers.DictField()
