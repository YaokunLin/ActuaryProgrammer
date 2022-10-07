import logging
from typing import Dict

from rest_framework import serializers
from core.serializers import UnixEpochDateField

from .models import (
    RingCentralAPICredentials,
    RingCentralSessionEvent,
    RingCentralCallLeg
)

from .publishers import (
    publish_ringcentral_create_call_audio_event
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

class RingCentralCallLegSerializer(serializers.ModelSerializer):
    publish = serializers.BooleanField(required=False, default=True, allow_null=True)
    time_start = UnixEpochDateField(required=False)

    class Meta:
        model = RingCentralCallLeg
        read_only_fields = ["id", "created_at", "modified_at"]
        fields = "__all__"

    def create(self, validated_data: Dict):

        # perform the create
        instance = super().create(validated_data=validated_data)
        log.info(validated_data)
        if validated_data['recordings']:
            publish_ringcentral_create_call_audio_event(
                peerlogic_call_id = validated_data['peerlogic_call_id'],
                peerlogic_call_partial_id = instance.id,
                ringcentral_recording_id = validated_data['ringcentral_recording_id'],
            )

        return instance
