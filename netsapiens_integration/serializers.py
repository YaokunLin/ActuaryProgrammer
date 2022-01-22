from rest_framework import serializers

from core.serializers import UnixEpochDateField
from .models import NetsapiensCallsSubscriptionEventExtract, NetsapiensCdr2Extract, NetsapiensSubscriptionClient


class NetsapiensCallsSubscriptionEventExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensCallsSubscriptionEventExtract
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


class NetsapiensSubscriptionClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensSubscriptionClient
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider"]
