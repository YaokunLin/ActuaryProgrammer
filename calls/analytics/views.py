from rest_framework import views
from rest_framework.response import Response
from calls.analytics.intents.field_choices import (
    CallOutcomeTypes,
    CallOutcomeReasonTypes,
    CallPurposeTypes,
)
from calls.analytics.participants.field_choices import EngagementPersonaTypes, NonAgentEngagementPersonaTypes


class CallAnalyticsFieldChoicesView(views.APIView):
    def get(self, request, format=None):
        result = {}
        result["engagement_persona_types"] = dict((y, x) for x, y in EngagementPersonaTypes.choices)
        result["non_agent_engagement_persona_types"] = dict((y, x) for x, y in NonAgentEngagementPersonaTypes.choices)
        result["call_purpose_types"] = dict((y, x) for x, y in CallPurposeTypes.choices)
        result["call_outcome_types"] = dict((y, x) for x, y in CallOutcomeTypes.choices)
        result["call_outcome_reason_types"] = dict((y, x) for x, y in CallOutcomeReasonTypes.choices)
        return Response(result)
