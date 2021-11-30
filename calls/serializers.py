from django.contrib.auth.models import Group

from rest_framework import serializers

from .models import (
    Call,
    CallLabel,
    TelecomCallerNameInfo,
)


class CallSerializer(serializers.ModelSerializer):
    domain = serializers.SlugRelatedField(queryset=Group.objects.all(), slug_field="name")

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

    
    def get_or_create(self, validated_data):
        return TelecomCallerNameInfo.objects.get_or_create_from_twilio(**validated_data)
        