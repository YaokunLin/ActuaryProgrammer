import logging
from typing import Optional, Union

from django.db.models import Count, Q, QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.aggregates import calculate_naept
from calls.analytics.intents.field_choices import CallPurposeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.analytics.query_filters import (
    BENCHMARK_PRACTICE_CALLS_FILTER,
    BENCHMARK_PRACTICE_FILTER,
    INBOUND_FILTER,
)
from calls.models import Call
from calls.validation import get_validated_call_dates
from core.models import Practice
from peerlogic.settings import (
    ANALYTICS_CACHE_VARY_ON_HEADERS,
    CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS,
    CACHE_TIME_ANALYTICS_SECONDS,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


# TODO: This is totally fudged
_AVG_VALUE_PER_APPOINTMENT_USD = 838.88


class OpportunitiesBenchmarks(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = _get_queryset_or_error_response(request, extra_filter=INBOUND_FILTER)
        if isinstance(calls_qs, Response):
            return calls_qs

        benchmark_practices_count = _get_benchmark_practices_count()

        new_appointment_filter = Q(call_purposes__call_purpose_type=CallPurposeTypes.NEW_APPOINTMENT)
        existing_patient_filter = Q(engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.EXISTING_PATIENT)
        new_patient_filter = Q(engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT)

        opportunities_qs = calls_qs.filter(new_appointment_filter & (existing_patient_filter | new_patient_filter))
        opportunities_by_outcome = opportunities_qs.values("call_purposes__outcome_results__call_outcome_type").annotate(count=Count("id"))
        d = {r["call_purposes__outcome_results__call_outcome_type"]: r["count"] for r in opportunities_by_outcome}

        total_count = opportunities_qs.count()
        won_count = d.get("success", 0)
        lost_count = d.get("failure", 0)
        n_a_count = total_count - (won_count + lost_count)
        average_opportunity_counts = {
            "total": total_count / benchmark_practices_count,
            "won": won_count / benchmark_practices_count,
            "lost": lost_count / benchmark_practices_count,
            "not_applicable": n_a_count / benchmark_practices_count,
        }
        average_opportunity_values = {
            "total": total_count / benchmark_practices_count * _AVG_VALUE_PER_APPOINTMENT_USD,
            "won": won_count / benchmark_practices_count * _AVG_VALUE_PER_APPOINTMENT_USD,
            "lost": lost_count / benchmark_practices_count * _AVG_VALUE_PER_APPOINTMENT_USD,
            "not_applicable": n_a_count / benchmark_practices_count * _AVG_VALUE_PER_APPOINTMENT_USD,
        }

        results = {
            "average_counts": average_opportunity_counts,
            "average_values": average_opportunity_values,
        }
        return Response(results)


class InboundCallerTypesBenchmarks(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = _get_queryset_or_error_response(request, extra_filter=INBOUND_FILTER)
        if isinstance(calls_qs, Response):
            return calls_qs

        benchmark_practices_count = _get_benchmark_practices_count()
        total_calls_by_naept = calculate_naept(calls_qs)

        for k, v in total_calls_by_naept.items():
            total_calls_by_naept[k] = v / benchmark_practices_count

        return Response(calculate_naept(calls_qs))


def _get_queryset_or_error_response(request: Request, extra_filter: Optional[Q] = None) -> Union[Response, QuerySet]:
    if extra_filter is None:
        extra_filter = Q()

    dates_info = get_validated_call_dates(query_data=request.query_params)
    dates_errors = dates_info.get("errors")

    errors = {}
    if dates_errors:
        errors.update(dates_errors)
    if errors:
        return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

    # date filters
    dates = dates_info.get("dates")
    call_start_time__gte = dates[0]
    call_start_time__lte = dates[1]
    dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}
    return Call.objects.filter(**dates_filter).filter(BENCHMARK_PRACTICE_CALLS_FILTER & extra_filter)


def _get_benchmark_practices_count() -> int:
    return Practice.objects.filter(BENCHMARK_PRACTICE_FILTER).count()
