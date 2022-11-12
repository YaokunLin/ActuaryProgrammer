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


class MyProfileUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["id", "name", "first_name", "last_name", "date_joined", "email", "username"]
        # TODO: change email (auth0 driven)
        read_only_fields = ["id", "name", "date_joined", "email", "username"]

    def update(self, instance, validated_data):
        # Always capitalize
        first_name = validated_data.get("first_name", instance.first_name).capitalize()
        validated_data["first_name"] = first_name
        last_name = validated_data.get("last_name", instance.last_name).capitalize()
        validated_data["last_name"] = last_name
        # For display
        validated_data["name"] = f"{first_name} {last_name}"

        super().update(instance, validated_data)

        return instance


class MyProfileAgentSerializer(serializers.ModelSerializer):
    user = MyProfileUserSerializer(required=False)

    class Meta:
        model = Agent
        fields = ["id", "practice", "user"]
        read_only_fields = ["id", "practice"]


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "password"]
