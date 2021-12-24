from django.contrib.auth.models import Group
from django_countries.serializers import CountryFieldMixin

from rest_framework import serializers

from core.models import PracticeTelecom

from .models import (
    Call,
    CallLabel,
    TelecomCallerNameInfo,
)


class CallSerializer(serializers.ModelSerializer):
    domain = serializers.SlugRelatedField(queryset=PracticeTelecom.objects.all(), slug_field="domain")

    class Meta:
        model = Call
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class CallLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLabel
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]


class TelecomCallerNameInfoSerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = TelecomCallerNameInfo
        fields = [
            "phone_number",
            "caller_name",
            "caller_name_type",
            "caller_name_type",
            "country_code",
            "source",
            "carrier_name",
            "carrier_type",
            "mobile_country_code",
            "mobile_network_code",
            "created_at",
            "modified_by",
            "modified_at",
        ]
        read_only_fields = ["created_at", "modified_by", "modified_at"]
