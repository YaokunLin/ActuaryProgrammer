import logging
from typing import Dict

from rest_framework import serializers

from core.serializers import UnixEpochDateField
from .models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscriptions,
    NetsapiensCallSubscriptionsEventExtract,
    NetsapiensCdr2Extract,
)
from .publishers import publish_netsapiens_cdr_saved


log = logging.getLogger(__name__)

class NetsapiensCallSubscriptionsEventExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensCallSubscriptionsEventExtract
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
    time_start = UnixEpochDateField()
    time_answer = UnixEpochDateField()
    time_release = UnixEpochDateField()
    time_ringing = UnixEpochDateField()

    class Meta:
        model = NetsapiensCdr2Extract
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = "__all__"


    def create(self, validated_data: Dict):
        netsapiens_call_subscription = validated_data.get("netsapiens_call_subscription")  # should never be None, change this line if we make it optional
        practice_id = netsapiens_call_subscription.practice_telecom.practice.id

        # cdr2_extract_data = validated_data.copy()
        # cdr2_extract_data.pop("")

        publish_netsapiens_cdr_saved(practice_id=practice_id, event=validated_data)
        return NetsapiensCdr2Extract.objects.create(**validated_data)


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


class NetsapiensCallSubscriptionsSerializer(serializers.ModelSerializer):
    call_subscription_uri = serializers.CharField(required=False)

    class Meta:
        model = NetsapiensCallSubscriptions
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "call_subscription_uri"]
        fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "source_id", "practice_telecom", "call_subscription_uri"]
