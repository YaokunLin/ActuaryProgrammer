from datetime import datetime
from rest_framework import serializers

from .models import Client, Patient, Practice, PracticeTelecom, User, VoipProvider


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
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"


class PracticeTelecomSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTelecom
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"


class VoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        read_only_fields = ["id", "created_at", "modified_by", "modified_at", "active"]
        fields = "__all__"


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"
