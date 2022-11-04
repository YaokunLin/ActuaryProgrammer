from django.utils import timezone
from rest_framework import serializers

from calls.models import Call
from ml.field_choices import ClassificationDomain
from ml.models import MLModel, MLModelResultHistory


class MLModelSerializer(serializers.ModelSerializer):
    model_version = serializers.RegexField(regex=r"^([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?$")

    class Meta:
        model = MLModel
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class MLModelResultHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModelResultHistory
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "call_id", "model_id", "run_id", "label", "score", "threshold"]


class MLModelResultHistoryCreateSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(required=False, allow_null=False, default=timezone.now())
    classification_domain = serializers.ChoiceField(choices=ClassificationDomain.choices, required=True, allow_null=False, allow_blank=False)
    call_id = serializers.PrimaryKeyRelatedField(queryset=Call.objects.all(), pk_field=serializers.CharField())
    model_id = serializers.PrimaryKeyRelatedField(queryset=MLModel.objects.all(), pk_field=serializers.CharField())
    run_id = serializers.CharField(required=True, allow_null=False, allow_blank=False, max_length=22, min_length=22)
    label = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    score = serializers.FloatField(required=True, allow_null=True)
    threshold = serializers.FloatField(required=True, allow_null=True)

    def to_internal_value(self, data: dict) -> dict:
        deserialized = super().to_internal_value(data)
        for field in {"call_id", "model_id"}:
            deserialized[field] = deserialized[field].id
        return deserialized


class MLModelResultHistoryBulkCreateSerializer(serializers.Serializer):
    records = MLModelResultHistoryCreateSerializer(many=True)
