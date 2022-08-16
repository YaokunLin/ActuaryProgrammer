from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from calls.models import Call, CallTranscript


class CallsFilter(filters.FilterSet):
    sip_caller_number__startswith = filters.CharFilter(field_name="sip_caller_number", lookup_expr="startswith")
    sip_callee_number__startswith = filters.CharFilter(field_name="sip_callee_number", lookup_expr="startswith")
    call_start_time = filters.DateFromToRangeFilter()

    class Meta:
        model = Call
        fields = {
            "id": ["exact"],  # for demo purposes
            "call_start_time": ["gte", "exact"],
            "call_end_time": ["lte", "exact"],
            "practice__id": ["exact"],
            "engaged_in_calls__non_agent_engagement_persona_type": ["exact"],
            "call_direction": ["exact"],
            "call_purposes__call_purpose_type": ["exact"],
            "call_purposes__outcome_results__call_outcome_type": ["exact"],
            "call_purposes__outcome_results__outcome_reason_results__call_outcome_reason_type": ["exact"],
            "call_sentiments__overall_sentiment_score": ["exact"],
            "mentioned_procedures__keyword": ["exact"],
        }


class CallTranscriptsSearchFilter(BaseFilterBackend):
    """Query Transcripts on the basis of `search` query param."""

    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get("search", None)
        if search_term:
            # Use the computed ts_vector directly to speed up the search.
            # Use filter and not "search" here
            return queryset.filter(transcript_text_tsvector=search_term)

        return queryset


class CallTranscriptsFilter(filters.FilterSet):
    class Meta:
        model = CallTranscript
        fields = {
            "mime_type": ["exact"],
            "status": ["exact"],
            "speech_to_text_model_type": ["exact"],
            "call__id": ["exact"],
        }
