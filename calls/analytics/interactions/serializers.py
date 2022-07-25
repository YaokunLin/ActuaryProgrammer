from rest_framework import serializers

from calls.analytics.interactions.models import AgentCallScore


class AgentCallScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCallScore
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
