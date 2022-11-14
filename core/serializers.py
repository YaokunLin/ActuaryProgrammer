from datetime import datetime

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.inline_serializers import (
    InlinePracticeTelecomSerializer,
    InlineUserSerializer,
)
from core.models import (
    Agent,
    Client,
    Organization,
    Patient,
    Practice,
    PracticeTelecom,
    User,
    VoipProvider,
)


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


class InlinePracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Practice
        fields = ["id", "name", "created_at", "modified_at", "active"]
        read_only_fields = ["id", "name", "created_at", "modified_at", "active"]


class OrganizationSerializer(serializers.ModelSerializer):

    practices = InlinePracticeSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active", "practices"]


class AdminOrganizationSerializer(serializers.ModelSerializer):
    practices = InlinePracticeSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class PracticeTelecomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "created_by",
            "modified_by",
            "modified_at",
            "voip_provider",
            "practice",
            "domain",
            "phone_sms",
            "phone_callback",
        ]


class PracticeTelecomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        fields = ["id", "practice", "voip_provider", "created_at", "modified_at"]
        read_only_fields = ["id", "created_at", "modified_at"]


class AdminPracticeTelecomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        fields = "__all__"
        read_only_fields = ["id", "created_at", "created_by", "modified_by", "modified_at"]


class VoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        fields = ["id", "created_at", "modified_at", "company_name"]
        read_only_fields = ["id", "created_at", "modified_at", "company_name"]


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
