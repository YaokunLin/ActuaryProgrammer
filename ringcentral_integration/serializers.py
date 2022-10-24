import logging
from typing import Dict

from rest_framework import serializers

from calls.models import Call
from core.serializers import UnixEpochDateField

from .models import (
    RingCentralAPICredentials,
    RingCentralCallLeg,
    RingCentralSessionEvent,
)
from .publishers import publish_ringcentral_call_leg_saved_event

log = logging.getLogger(__name__)


class RingCentralSessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RingCentralSessionEvent
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
    time_start = UnixEpochDateField(required=False)
    voip_provider_id = serializers.CharField(required=False)
    peerlogic_call_partial_id = serializers.CharField(required=False)
    class Meta:
        model = RingCentralCallLeg
        read_only_fields = ["id", "created_at", "modified_at"]
        fields = "__all__"

    def create(self, validated_data: Dict):
        # Grab the Voip provider and call_partial_id used in the create call function
        voip_provider_id = validated_data.pop("voip_provider_id", None)
        call_partial_id = validated_data.pop("peerlogic_call_partial_id", None)

        # perform the create
        instance = super().create(validated_data=validated_data)
        log.info(validated_data)

        peerlogic_call = Call.objects.get(pk=validated_data["peerlogic_call_id"])
        practice_id = peerlogic_call.practice.id
        if "recording" in validated_data:
            publish_ringcentral_call_leg_saved_event(
                practice_id=practice_id,
                voip_provider_id=voip_provider_id,
                peerlogic_call_id=validated_data["peerlogic_call_id"],
                peerlogic_call_partial_id=call_partial_id,
                ringcentral_recording_id=validated_data["recording"],
            )

        return instance
