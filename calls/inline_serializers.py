import logging

from rest_framework import serializers

from calls.analytics.intents.models import CallMentionedProcedure, CallOutcome, CallOutcomeReason, CallPurpose
from calls.analytics.participants.models import AgentEngagedWith

# Get an instance of a logger
log = logging.getLogger(__name__)


class InlineCallOutcomeReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallOutcomeReason
        fields = ["id", "call_outcome_reason_type"]
        read_only_fields = ["id", "call_outcome_reason_type"]


class InlineCallOutcomeSerializer(serializers.ModelSerializer):
    outcome_reason_results = InlineCallOutcomeReasonSerializer(many=True, read_only=True)

    class Meta:
        model = CallOutcome
        fields = ["id", "call_outcome_type", "outcome_reason_results"]
        read_only_fields = ["id", "call_outcome_type"]


class InlineCallPurposeSerializer(serializers.ModelSerializer):
    outcome_results = InlineCallOutcomeSerializer(many=True, read_only=True)

    class Meta:
        model = CallPurpose
        fields = ["id", "call_purpose_type", "outcome_results"]
        read_only_fields = ["id", "call_purpose_type"]


class InlineAgentEngagedWithSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentEngagedWith
        fields = ["id", "non_agent_engagement_persona_type"]
        read_only_fields = ["id", "non_agent_engagement_persona_type"]


class InlineCallMentionedProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedProcedure
        fields = ["id", "keyword"]
        read_only_fields = ["id", "keyword"]
