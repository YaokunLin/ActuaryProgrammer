from django.contrib.auth.models import Group

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


class TelecomCallerNameInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelecomCallerNameInfo
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
