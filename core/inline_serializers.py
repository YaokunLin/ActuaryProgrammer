from rest_framework import serializers

from core.models import PracticeTelecom, User, VoipProvider


class InlineVoipProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoipProvider
        fields = ["id", "integration_type", "company_name"]
        read_only_fields = ["id", "integration_type", "company_name"]


class InlinePracticeTelecomSerializer(serializers.ModelSerializer):
    voip_provider = InlineVoipProviderSerializer(read_only=True)

    class Meta:
        model = PracticeTelecom
        fields = ["id", "voip_provider"]
        read_only_fields = ["id", "voip_provider"]


class InlineUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name"]
        read_only_fields = ["id", "auth0_id", "objects"]
