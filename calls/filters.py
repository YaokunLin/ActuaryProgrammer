from datetime import datetime, time
from logging import getLogger

from django import forms
from django.db.models import Q
from django_filters import rest_framework as filters
from django_filters.filters import RangeField
from django_filters.utils import handle_timezone
from django_filters.widgets import DateRangeWidget
from rest_framework.filters import BaseFilterBackend

from calls.analytics.intents.field_choices import (
    CallOutcomeReasonTypes,
    CallOutcomeTypes,
    CallPurposeTypes,
)
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.field_choices import TranscriptTypes
from calls.models import Call, CallTranscript
from core.models import MarketingCampaignPhoneNumber

log = getLogger(__name__)


class _UnaldultratedDateRangeField(RangeField):
    """
    Same as django_filters.fields.DateRangeField except it doesn't set the to_date to use 23:59:59.999999
    """

    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (forms.DateField(), forms.DateField())
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            start_date, stop_date = data_list
            if start_date:
                start_date = handle_timezone(datetime.combine(start_date, time.min), False)
            if stop_date:
                stop_date = handle_timezone(datetime.combine(stop_date, time.min), False)
            return slice(start_date, stop_date)
        return None


class _UnaldultratedDateFromToRangeFilter(filters.RangeFilter):
    """
    Same as django_filters.filters.DateFromToRangeFilter except it doesn't set the to_date to use 23:59:59.999999
    """

    field_class = _UnaldultratedDateRangeField


class CallsFilter(filters.FilterSet):
    sip_caller_number__startswith = filters.CharFilter(field_name="sip_caller_number", lookup_expr="startswith")
    sip_callee_number__startswith = filters.CharFilter(field_name="sip_callee_number", lookup_expr="startswith")
    call_start_time = _UnaldultratedDateFromToRangeFilter()
    marketing_campaign_name = filters.CharFilter(method="filter_marketing_campaign_name")
    call_purposes__call_purpose_type = filters.MultipleChoiceFilter(choices=CallPurposeTypes.choices, method="_filter_call_purpose_fields")
    call_purposes__outcome_results__call_outcome_type = filters.MultipleChoiceFilter(choices=CallOutcomeTypes.choices, method="_filter_call_purpose_fields")
    call_purposes__outcome_results__outcome_reason_results__call_outcome_reason_type = filters.MultipleChoiceFilter(
        choices=CallOutcomeReasonTypes.choices, method="_filter_call_purpose_fields"
    )
    engaged_in_calls__non_agent_engagement_persona_type = filters.MultipleChoiceFilter(choices=NonAgentEngagementPersonaTypes.choices)

    def __init__(self, *args, **kwargs):
        self.purpose_filters_applied = False
        super().__init__(*args, **kwargs)

    def filter_marketing_campaign_name(self, queryset, name, value):
        practice_id = self.request.query_params.get("practice__id")
        if not practice_id:
            return queryset

        try:
            campaign_phone_number = MarketingCampaignPhoneNumber.objects.get(practice_id=practice_id, name=value)
        except MarketingCampaignPhoneNumber.DoesNotExist:
            return queryset

        return queryset.filter(sip_callee_number=campaign_phone_number.phone_number)

    def _filter_call_purpose_fields(self, queryset, name, value):
        if not self.purpose_filters_applied:
            call_purpose_key = "call_purposes__call_purpose_type"
            call_outcome_key = "call_purposes__outcome_results__call_outcome_type"
            call_outcome_reason_key = "call_purposes__outcome_results__outcome_reason_results__call_outcome_reason_type"
            filters = Q()
            for key in {call_purpose_key, call_outcome_key, call_outcome_reason_key}:
                if key in self.request.query_params:
                    value = self.request.query_params.getlist(key)
                    if len(value) > 1:
                        filters = filters & Q(**{f"{key}__in": value})
                    else:
                        filters = filters & Q(**{key: value[0]})

            self.purpose_filters_applied = True
            log.debug("Filtering call purpose fields for %s: %s", name, filters)
            return queryset.filter(filters)
        log.debug("Skipping filtering for %s (call purpose filters already applied)", name)
        return queryset

    class Meta:
        model = Call
        fields = {
            "id": ["exact"],
            "practice__id": ["exact"],
            "call_direction": ["exact"],
            "call_connection": ["exact"],
            "went_to_voicemail": ["exact"],
            "checked_voicemail": ["exact"],
            "call_sentiments__overall_sentiment_score": ["exact"],
            "mentioned_companies__keyword": ["exact"],
            "mentioned_insurances__keyword": ["exact"],
            "mentioned_procedures__keyword": ["exact"],
            "mentioned_products__keyword": ["exact"],
            "mentioned_symptoms__keyword": ["exact"],
            "sip_caller_extension": ["exact"],
        }


class CallSearchFilter(BaseFilterBackend):
    """Query Transcripts on the basis of `search` query param."""

    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get("search", None)
        if search_term:
            # Use the computed ts_vector directly to speed up the search.
            # Use filter and not "search" here
            return queryset.filter(calltranscript__transcript_text_tsvector=search_term, calltranscript__transcript_type=TranscriptTypes.FULL_TEXT)

        return queryset


class CallTranscriptsSearchFilter(BaseFilterBackend):
    """Query Transcripts on the basis of `search` query param."""

    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get("search", None)
        if search_term:
            # Use the computed ts_vector directly to speed up the search.
            # Use filter and not "search" here
            return queryset.filter(transcript_text_tsvector=search_term, calltranscript__transcript_type=TranscriptTypes.FULL_TEXT)

        return queryset


class CallTranscriptsFilter(filters.FilterSet):
    class Meta:
        model = CallTranscript
        fields = {
            "call__id": ["exact"],
            "mime_type": ["exact"],
            "speech_to_text_model_type": ["exact"],
            "status": ["exact"],
            "transcript_type": ["exact"],
        }
