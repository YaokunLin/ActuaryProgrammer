import logging
from typing import Dict

from rest_framework import serializers

from core.models import PracticeTelecom
from core.serializers import UnixEpochDateField
from .models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscription,
    NetsapiensCallSubscriptionEventExtract,
    NetsapiensCdr2Extract,
)
from .publishers import (
    publish_netsapiens_cdr_saved_event,
    publish_netsapiens_cdr_linked_to_call_partial_event,
)


log = logging.getLogger(__name__)


class NetsapiensCallSubscriptionEventExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensCallSubscriptionEventExtract
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = "__all__"

    # Takes the unvalidated incoming data as input and return the validated data that will be made available as serializer.validated_data internal value runs first
    def to_internal_value(self, data):
        # time_answer may come in as all zeros which will fail the datetime validator
        # this is effectively a Null or None value indicating there wasn't a time_answer
        time_answer = data.get("time_answer")
        if time_answer == "0000-00-00 00:00:00":
            time_answer = None

        data["time_answer"] = time_answer

        return data


class NetsapiensCdr2ExtractSerializer(serializers.ModelSerializer):
    publish = serializers.BooleanField(required=False, default=True, allow_null=True)
    time_start = UnixEpochDateField(required=False)
    time_answer = UnixEpochDateField(required=False)
    time_release = UnixEpochDateField(required=False)
    
    cdrr_batch_hold = UnixEpochDateField(required=False)
    cdrr_time_start = UnixEpochDateField(required=False)
    cdrr_time_answer = UnixEpochDateField(required=False)
    cdrr_time_release = UnixEpochDateField(required=False)
    cdrr_time_ringing = UnixEpochDateField(required=False)

    class Meta:
        model = NetsapiensCdr2Extract
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = "__all__"

    def create(self, validated_data: Dict):
        publish = validated_data.pop("publish", True)

        # perform the create
        instance = super().create(validated_data=validated_data)

        # extract values for the event and publish representation
        practice_id = (
            instance.netsapiens_call_subscription.practice_telecom.practice.id
        )  # "netsapiens_call_subscription" should never be None, change this line if we make it optional
        if publish:
            publish_netsapiens_cdr_saved_event(practice_id=practice_id, event=self.to_representation(instance))

        return instance

    def update(self, instance: NetsapiensCdr2Extract, validated_data: Dict) -> NetsapiensCdr2Extract:
        publish = validated_data.pop("publish", True)
        instance: NetsapiensCdr2Extract = super().update(instance, validated_data)
        if self._is_call_linked_update(instance) and publish:
            # "netsapiens_call_subscription" should never be None, change this line if we make it optional
            practice_telecom: PracticeTelecom = instance.netsapiens_call_subscription.practice_telecom
            practice_id = practice_telecom.practice.id
            voip_provider_id = practice_telecom.voip_provider.id
            publish_netsapiens_cdr_linked_to_call_partial_event(
                practice_id=practice_id, voip_provider_id=voip_provider_id, event=self.to_representation(instance)
            )

        return instance

    def _is_call_linked_update(self, instance: NetsapiensCdr2Extract) -> bool:
        return instance.peerlogic_call_id and instance.peerlogic_call_partial_id


class NetsapiensAPICredentialsReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "active"]
        fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "voip_provider", "api_url", "client_id", "username", "active"]


class NetsapiensAPICredentialsWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "active"]
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


class AdminNetsapiensAPICredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
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


class NetsapiensCallSubscriptionSerializer(serializers.ModelSerializer):
    call_subscription_uri = serializers.CharField(required=False)

    class Meta:
        model = NetsapiensCallSubscription
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "call_subscription_uri"]
        fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "source_id", "practice_telecom", "call_subscription_uri"]
