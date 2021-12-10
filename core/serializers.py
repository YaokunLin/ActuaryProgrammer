from rest_framework import serializers

from .models import Client, Patient


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "group", "rest_base_url"]


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"
