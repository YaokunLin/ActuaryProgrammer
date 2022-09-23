import logging
from typing import Dict

from rest_framework import serializers

from .models import (
    RingCentralAPICredentials,
    RingCentralSessionEvent
)

log = logging.getLogger(__name__)

class RingCentralSessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RingCentralSessionEvent
        # read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = "__all__"
    
    def create(self, validated_data: Dict):
        instance = super().create(validated_data)

        return instance
    
class AdminRingCentralAPICredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RingCentralAPICredentials
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = [
            "id",
            "created_by",
            "created_at",
            "modified_by",
            "modified_at",
            "voip_provider",
            "api_url",
            "client_id",
            "client_secret",
            "username",
            "password",
            "active",
        ]