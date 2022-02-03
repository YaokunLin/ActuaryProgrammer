from rest_framework import serializers

from core.serializers import UnixEpochDateField
from .models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscriptions,
    NetsapiensCallSubscriptionsEventExtract,
    NetsapiensCdr2Extract,
)


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
