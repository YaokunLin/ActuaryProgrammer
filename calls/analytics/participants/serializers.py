from rest_framework import serializers

from calls.analytics.participants.models import AgentEngagedWith


class AgentEngagedWithSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentEngagedWith
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
