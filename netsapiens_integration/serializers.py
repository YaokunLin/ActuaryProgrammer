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
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"


class NetsapiensCdr2ExtractSerializer(serializers.ModelSerializer):
    time_start = UnixEpochDateField()
    time_answer = UnixEpochDateField()
    time_release = UnixEpochDateField()
    time_ringing = UnixEpochDateField()

    class Meta:
        model = NetsapiensCdr2Extract
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"


class NetsapiensAPICredentialsReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "api_url", "client_id", "username", "active"]


class NetsapiensAPICredentialsWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "api_url", "client_id", "client_secret", "username", "password", "active"]


class AdminNetsapiensAPICredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "api_url", "client_id", "client_secret", "username", "password", "active"]


class NetsapiensCallSubscriptionsSerializer(serializers.ModelSerializer):
    call_subscription_uri = serializers.CharField(required=False)

    class Meta:
        model = NetsapiensCallSubscriptions
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "call_subscription_uri"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "call_subscription_uri"]
