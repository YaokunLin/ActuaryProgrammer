from rest_framework import serializers

from calls.analytics.participants.models import AgentAssignedCall, AgentEngagedWith
from calls.models import Call
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
        call: Call = Call.objects.get(pk=self.context["view"].kwargs["call_pk"])
        validated_data["call"] = call

        # there should only be one neapt for a call to ensure analytics / counting goes smoothly
        # when we reprocess, update the existing neapt
        engaged_in_calls = call.engaged_in_calls
        if engaged_in_calls.exists():
            agent_engaged_with = engaged_in_calls.first()  # should only be one
            return self.update(agent_engaged_with, validated_data)

        # first time processing
        return AgentEngagedWith.objects.create(**validated_data)

    class Meta:
        model = AgentEngagedWith
        fields = ["id", "non_agent_engagement_persona_type", "raw_non_agent_engagement_persona_model_run_id", "non_agent_engagement_persona_model_run"]
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
