import logging
from typing import Optional, Union

from django.db.models import Count, Q, QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.aggregates import calculate_call_counts
from calls.analytics.constants import AVG_VALUE_PER_APPOINTMENT_USD
from calls.analytics.query_filters import (
    BENCHMARK_PRACTICE_CALLS_FILTER,
    BENCHMARK_PRACTICE_FILTER,
    INBOUND_FILTER,
    OPPORTUNITIES_FILTER,
)
from calls.models import Call
from calls.validation import get_validated_call_dates, get_validated_call_direction
from core.models import Practice
from peerlogic.settings import (
    ANALYTICS_CACHE_VARY_ON_HEADERS,
    CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS,
    CACHE_TIME_ANALYTICS_SECONDS,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class OpportunitiesBenchmarksView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = _get_queryset_or_error_response(request, extra_filter=INBOUND_FILTER)
        if isinstance(calls_qs, Response):
            return calls_qs

        benchmark_practices_count = _get_benchmark_practices_count()
        opportunities_qs = calls_qs.filter(OPPORTUNITIES_FILTER)

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
            "total": total_count / benchmark_practices_count * AVG_VALUE_PER_APPOINTMENT_USD,
            "won": won_count / benchmark_practices_count * AVG_VALUE_PER_APPOINTMENT_USD,
            "lost": lost_count / benchmark_practices_count * AVG_VALUE_PER_APPOINTMENT_USD,
            "not_applicable": n_a_count / benchmark_practices_count * AVG_VALUE_PER_APPOINTMENT_USD,
        }

        results = {
            "average_counts": average_opportunity_counts,
            "average_values": average_opportunity_values,
        }
        return Response(results)


class CallCountsBenchmarksView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = _get_queryset_or_error_response(request)
        if isinstance(calls_qs, Response):
            return calls_qs

        benchmark_practices_count = _get_benchmark_practices_count()
        call_counts = calculate_call_counts(calls_qs)
        for section_name in {"call_total", "call_connected_total", "call_seconds_total", "call_answered_total", "call_voicemail_total", "call_missed_total"}:
            call_counts[section_name] = call_counts[section_name] / benchmark_practices_count
        for section_name in {"call_sentiment_counts", "call_direction_counts", "call_naept_counts", "call_purpose_counts"}:
            section = call_counts[section_name]
            for k, v in section.items():
                section[k] = v / benchmark_practices_count

        return Response(call_counts)


def _get_queryset_or_error_response(request: Request, extra_filter: Optional[Q] = None) -> Union[Response, QuerySet]:
    if extra_filter is None:
        extra_filter = Q()

    dates_info = get_validated_call_dates(query_data=request.query_params)
    dates_errors = dates_info.get("errors")

    valid_call_direction, call_drection_errors = get_validated_call_direction(request)

    errors = {}
    if dates_errors:
        errors.update(dates_errors)
    if call_drection_errors:
        errors.update(call_drection_errors)
    if errors:
        return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

    # date filters
    dates = dates_info.get("dates")
    call_start_time__gte = dates[0]
    call_start_time__lte = dates[1]
    dates_filter = Q(call_start_time__gte=call_start_time__gte, call_start_time__lte=call_start_time__lte)

    call_direction_filter = Q()
    if valid_call_direction:
        call_direction_filter = Q(call_direction=valid_call_direction)

    return Call.objects.filter(BENCHMARK_PRACTICE_CALLS_FILTER & dates_filter & call_direction_filter & extra_filter)


def _get_benchmark_practices_count() -> int:
    return Practice.objects.filter(BENCHMARK_PRACTICE_FILTER).count()
