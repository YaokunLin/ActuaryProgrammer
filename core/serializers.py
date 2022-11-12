from datetime import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.inline_serializers import InlinePracticeTelecomSerializer, InlineUserSerializer

from core.models import Agent, Client, Organization, Patient, Practice, PracticeTelecom, User, VoipProvider


class UnixEpochDateField(serializers.DateTimeField):
    def to_representation(self, value: datetime) -> int:
        """Return epoch time for a datetime object or ``None``"""
        import time

        try:
            return int(time.mktime(value.timetuple()))
        except (AttributeError, TypeError):
            return None

    def to_internal_value(self, value: float) -> datetime:
        return datetime.fromtimestamp(int(value))


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"


class AdminPracticeSerializer(serializers.ModelSerializer):
    practice_telecom = InlinePracticeTelecomSerializer(read_only=True)

    class Meta:
        model = Practice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class PracticeSerializer(serializers.ModelSerializer):
    practice_telecom = InlinePracticeTelecomSerializer(read_only=True)

    class Meta:
        model = Practice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active"]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active"]

    def create(self, validated_data):
        request = self.context.get("request")
        name = validated_data.get("name")

        # TODO: do we want active: False this model for Peerlogic Validation?
        organization = Organization.objects.create(**validated_data)
        practice = Practice.objects.create(organization=organization, name=name, active=False)
        Agent.objects.create(practice=practice, user=request.user)

        return organization


class AdminOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class PracticeTelecomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "practice", "domain", "phone_sms", "phone_callback"]


class AdminPracticeTelecomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class VoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        fields = ["id", "created_at", "modified_by", "modified_at", "company_name"]
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "company_name"]


class AdminVoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class AgentSerializer(serializers.ModelSerializer):
    user = InlineUserSerializer(required=False)

    class Meta:
        model = Agent
        fields = ["id", "practice", "user"]
        read_only_fields = ["id", "practice", "user"]


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "password"]
