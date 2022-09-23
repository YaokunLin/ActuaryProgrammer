import logging
from contextlib import suppress
from typing import Dict, List

from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.query_filters import (
    BENCHMARK_PRACTICE_CALLS_FILTER,
    NAEPT_PATIENT_FILTER,
)
from calls.models import Call
from calls.validation import (
    get_validated_call_dates,
    get_validated_call_direction,
    get_validated_organization_id,
    get_validated_practice_id,
    get_validated_query_param_bool,
)
from peerlogic.settings import (
    ANALYTICS_CACHE_VARY_ON_HEADERS,
    CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS,
    CACHE_TIME_ANALYTICS_SECONDS,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class _TopMentionedViewBase(views.APIView):

    _RESOURCE_NAME: str = None

    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request: Request, format=None) -> Response:
        # TODO: Use app settings for pagination limits and use shared code for getting size here
        size = 10
        with suppress(Exception):
            size = max(0, min(50, int(request.query_params.get("size", size))))

        is_benchmark = get_validated_query_param_bool(request, "benchmark", False)
        valid_call_direction, call_drection_errors = get_validated_call_direction(request)
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_organization_id, organization_errors = get_validated_organization_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if organization_errors:
            errors.update(organization_errors)
        if call_drection_errors:
            errors.update(call_drection_errors)
        if not practice_errors and not organization_errors and bool(valid_practice_id) == bool(valid_organization_id) and not is_benchmark:
            error_message = "practice__id or organization__id or benchmark must be provided, but not more than one of them."
            errors.update({"practice__id": error_message, "organization__id": error_message, "benchmark": error_message})
        elif is_benchmark and valid_practice_id or valid_organization_id:
            error_message = "practice__id or organization__id or benchmark must be provided, but not more than one of them."
            errors.update({"practice__id": error_message, "organization__id": error_message, "benchmark": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice_filter = Q()
        organization_filter = Q()
        if is_benchmark:
            practice_filter = BENCHMARK_PRACTICE_CALLS_FILTER
        else:
            if valid_practice_id:
                practice_filter = Q(practice__id=valid_practice_id)
            if valid_organization_id:
                organization_filter = Q(practice__organization_id=valid_organization_id)

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = Q(call_start_time__gte=call_start_time__gte, call_start_time__lte=call_start_time__lte)

        call_direction_filter = Q()
        if valid_call_direction:
            call_direction_filter = Q(call_direction=valid_call_direction)

        all_filters = NAEPT_PATIENT_FILTER & dates_filter & practice_filter & organization_filter & call_direction_filter
        return Response(self._get_top_mentions(all_filters, self._RESOURCE_NAME, size))

    def _get_top_mentions(self, call_filters: Q, resource_name: str, size: int) -> Dict:
        mentioned_resource_name = f"mentioned_{resource_name}"
        mentioned_resource_keyword = f"{mentioned_resource_name}__keyword"
        count_label = "count"
        non_null_keyword_filter = Q(**{f"{mentioned_resource_keyword}__isnull": False})
        calls_qs = Call.objects.select_related(mentioned_resource_name).filter(call_filters & non_null_keyword_filter)
        top_mentions = calls_qs.values(mentioned_resource_keyword).annotate(count=Count("id")).order_by(f"-{count_label}")[:size]
        top_mentions = [{"keyword": i[mentioned_resource_keyword], count_label: i[count_label]} for i in top_mentions]
        self._normalize_values(top_mentions)
        return {"top_mentions": top_mentions}

    @staticmethod
    def _normalize_values(values: List[Dict]) -> None:
        """
        Overload this to change behavior normalizing values in-place
        """
        keyword_label = "keyword"
        for v in values:
            value = v[keyword_label].strip()
            if value and value[0].islower():
                value = value.title()
            v[keyword_label] = value


class TopCompaniesMentionedView(_TopMentionedViewBase):
    _RESOURCE_NAME = "companies"


class TopInsurancesMentionedView(_TopMentionedViewBase):
    _RESOURCE_NAME = "insurances"


class TopProceduresMentionedView(_TopMentionedViewBase):
    _RESOURCE_NAME = "procedures"


class TopProductsMentionedView(_TopMentionedViewBase):
    _RESOURCE_NAME = "products"


class TopSymptomsMentionedView(_TopMentionedViewBase):
    _RESOURCE_NAME = "symptoms"
