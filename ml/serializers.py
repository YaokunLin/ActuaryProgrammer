from rest_framework import serializers

from ml.models import MLModel, MLModelResultHistory


class MLModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class MLModelResultHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModelResultHistory
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
