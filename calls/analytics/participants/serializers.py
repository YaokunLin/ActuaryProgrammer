from rest_framework import serializers

from calls.models import Call
from calls.analytics.participants.models import (
    AgentAssignedCall,
    AgentEngagedWith,
)
from core.serializers import AgentSerializer


class AgentAssignedCallSerializer(serializers.ModelSerializer):
    agent = AgentSerializer(required=False)


    class Meta:
        model = AgentAssignedCall
        fields = ["id", "agent", "call"]
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class AgentEngagedWithReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = AgentEngagedWith
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class AgentEngagedWithWriteSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        call = Call.objects.get(pk=self.context["view"].kwargs["call_pk"])
        validated_data["call"] = call
        return AgentEngagedWith.objects.create(**validated_data)

    class Meta:
        model = AgentEngagedWith
        fields = ["id", "non_agent_engagement_persona_type", "raw_non_agent_engagement_persona_model_run_id", "non_agent_engagement_persona_model_run"]
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
