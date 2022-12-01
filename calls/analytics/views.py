from rest_framework import views
from rest_framework.response import Response

from calls.analytics.intents.field_choices import (
    CallOutcomeReasonTypes,
    CallOutcomeTypes,
    CallPurposeTypes,
)
from calls.analytics.interactions.field_choices import AgentInteractionMetricTypes
from calls.analytics.participants.field_choices import (
    EngagementPersonaTypes,
    NonAgentEngagementPersonaTypes,
)


class CallAnalyticsFieldChoicesView(views.APIView):
    def get(self, request, format=None):
        result = {}
        result["agent_interaction_metric_types"] = dict(
            (str(y), x) for x, y in AgentInteractionMetricTypes.choices
        )  # retain as choices / non-dynamic for now, keys MUST be cast as strings here
        result["engagement_persona_types"] = dict((y, x) for x, y in EngagementPersonaTypes.choices)
        result["non_agent_engagement_persona_types"] = dict((y, x) for x, y in NonAgentEngagementPersonaTypes.choices)
        result["call_purpose_types"] = dict((y, x) for x, y in CallPurposeTypes.choices)
        result["call_outcome_types"] = dict((y, x) for x, y in CallOutcomeTypes.choices)
        result["call_outcome_reason_types"] = dict((str(y), x) for x, y in CallOutcomeReasonTypes.choices)  # key MUST be cast to a string
        return Response(result)
