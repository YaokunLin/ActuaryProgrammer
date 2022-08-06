from rest_framework import serializers

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


class AgentEngagedWithSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentEngagedWith
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
