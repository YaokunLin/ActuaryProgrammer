from rest_framework import serializers

from .models import Client, Patient, VoipProvider


class UnixEpochDateField(serializers.DateTimeField):
    def to_representation(self, value):
        """Return epoch time for a datetime object or ``None``"""
        import time

        try:
            return int(time.mktime(value.timetuple()))
        except (AttributeError, TypeError):
            return None

    def to_internal_value(self, value):
        import datetime

        return datetime.datetime.fromtimestamp(int(value))


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


class VoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"
