from django_filters import rest_framework as filters

from calls.models import Call


class CallsFilter(filters.FilterSet):
    sip_caller_number_search = filters.CharFilter(field_name="sip_caller_number", lookup_expr="icontains")
    sip_callee_number_search = filters.CharFilter(field_name="sip_callee_number", lookup_expr="icontains")

    class Meta:
        model = Call
        fields = [
            "engaged_in_calls__non_agent_engagement_persona_type",
            "call_direction",
            "call_purposes__call_purpose_type",
            "call_purposes__outcome_results__call_outcome_type",
            "call_purposes__outcome_results__outcome_reason_results__call_outcome_reason_type",
            "mentioned_procedures__keyword",
        ]
