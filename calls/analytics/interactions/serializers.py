from rest_framework import serializers

from calls.analytics.interactions.models import AgentCallScore, AgentCallScoreMetric


class AgentCallScoreMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCallScoreMetric
        fields = ["id", "metric", "group"]


class AgentCallScoreReadSerializer(serializers.ModelSerializer):
    metric = AgentCallScoreMetricSerializer(required=True)

    class Meta:
        model = AgentCallScore
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class AgentCallScoreWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCallScore
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
