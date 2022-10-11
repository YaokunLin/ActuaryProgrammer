import logging
from typing import Optional, Union

from django.db.models import Count, Q, QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_counts,
    round_if_float,
    safe_divide,
)
from calls.analytics.constants import AVG_VALUE_PER_APPOINTMENT_USD
from calls.analytics.query_filters import (
    INBOUND_FILTER,
    INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER,
    INDUSTRY_AVERAGES_PRACTICE_FILTER,
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


class OpportunitiesIndustryAveragesView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = _get_queryset_or_error_response(request, extra_filter=INBOUND_FILTER, allow_call_direction_filter=False)
        if isinstance(calls_qs, Response):
            return calls_qs

        industry_averages_practices_count = _get_industry_averages_practices_count()
        opportunities_qs = calls_qs.filter(OPPORTUNITIES_FILTER)

        opportunities_by_outcome = opportunities_qs.values("call_purposes__outcome_results__call_outcome_type").annotate(count=Count("id"))
        d = {r["call_purposes__outcome_results__call_outcome_type"]: r["count"] for r in opportunities_by_outcome}

        total_count = opportunities_qs.count()
        won_count = d.get("success", 0)
        lost_count = d.get("failure", 0)
        open_count = total_count - (won_count + lost_count)
        average_opportunity_counts = {
            "total": safe_divide(total_count, industry_averages_practices_count),
            "won": safe_divide(won_count, industry_averages_practices_count),
            "lost": safe_divide(lost_count, industry_averages_practices_count),
            "open": safe_divide(open_count, industry_averages_practices_count),
        }
        average_opportunity_values = {
            "total": round_if_float(safe_divide(total_count, industry_averages_practices_count, should_round=False) * AVG_VALUE_PER_APPOINTMENT_USD),
            "won": round_if_float(safe_divide(won_count, industry_averages_practices_count, should_round=False) * AVG_VALUE_PER_APPOINTMENT_USD),
            "lost": round_if_float(safe_divide(lost_count, industry_averages_practices_count, should_round=False) * AVG_VALUE_PER_APPOINTMENT_USD),
            "open": round_if_float(safe_divide(open_count, industry_averages_practices_count, should_round=False) * AVG_VALUE_PER_APPOINTMENT_USD),
        }

        results = {
            "average_counts": average_opportunity_counts,
            "average_values": average_opportunity_values,
        }
        return Response(results)


class CallCountsIndustryAveragesView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = _get_queryset_or_error_response(request)
        if isinstance(calls_qs, Response):
            return calls_qs

        industry_averages_practices_count = _get_industry_averages_practices_count()
        call_counts = calculate_call_counts(calls_qs)
        for section_name in {"call_total", "call_connected_total", "call_seconds_total", "call_answered_total", "call_voicemail_total", "call_missed_total"}:
            call_counts[section_name] = safe_divide(call_counts[section_name], industry_averages_practices_count)
        for section_name in {"call_sentiment_counts", "call_direction_counts", "call_naept_counts", "call_purpose_counts"}:
            section = call_counts[section_name]
            for k, v in section.items():
                section[k] = safe_divide(v, industry_averages_practices_count)

        return Response(call_counts)


def _get_queryset_or_error_response(request: Request, extra_filter: Optional[Q] = None, allow_call_direction_filter: bool = True) -> Union[Response, QuerySet]:
    if extra_filter is None:
        extra_filter = Q()

    dates_info = get_validated_call_dates(query_data=request.query_params)
    dates_errors = dates_info.get("errors")

    call_direction_filter = Q()

    errors = {}
    if dates_errors:
        errors.update(dates_errors)
    if allow_call_direction_filter:
        valid_call_direction, call_direction_errors = get_validated_call_direction(request)
        if call_direction_errors:
            errors.update(call_direction_errors)
        elif valid_call_direction:
            call_direction_filter = Q(call_direction=valid_call_direction)
    if errors:
        return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

    # date filters
    dates = dates_info.get("dates")
    call_start_time__gte = dates[0]
    call_start_time__lte = dates[1]
    dates_filter = Q(call_start_time__gte=call_start_time__gte, call_start_time__lte=call_start_time__lte)

    return Call.objects.filter(INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER & dates_filter & call_direction_filter & extra_filter)


def _get_industry_averages_practices_count() -> int:
    return Practice.objects.filter(INDUSTRY_AVERAGES_PRACTICE_FILTER).count()
