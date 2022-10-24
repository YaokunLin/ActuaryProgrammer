from rest_framework import serializers

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
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
