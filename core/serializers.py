from datetime import datetime
from rest_framework import serializers

from .models import Agent, Client, Patient, Practice, PracticeTelecom, User, VoipProvider


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


class PracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Practice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class PracticeTelecomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class VoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active"]


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ["id", "auth0_id", "objects"]


class AgentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)

    class Meta:
        model = Agent
        fields = ["id", "practice", "user", "user"]
        read_only_fields = ["id", "practice", "user"]


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "password"]
