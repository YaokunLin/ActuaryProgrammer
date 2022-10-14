import logging
from contextlib import suppress
from copy import deepcopy
from functools import partial
from typing import Dict, List

from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.aggregates import (
    divide_safely_if_possible,
    map_nested_objs,
    safe_divide,
)
from calls.analytics.query_filters import (
    INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER,
    INDUSTRY_AVERAGES_PRACTICE_FILTER,
    NAEPT_PATIENT_FILTER,
)
from calls.models import Call
from calls.validation import (
    get_validated_call_dates,
    get_validated_call_direction,
    get_validated_practice_id,
    get_validated_query_param_bool,
)
from core.models import Practice
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
        #
        # collect parameters
        #
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        valid_call_direction, call_direction_errors = get_validated_call_direction(request=request)

        industry_average_parameter_name = "industry_average"
        is_industry_averages_request = get_validated_query_param_bool(request, industry_average_parameter_name, False)
        practice_id_parameter_name = "practice__id"
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)

        size = 10  # TODO: Use app settings for pagination limits and use shared code for getting size here
        with suppress(Exception):
            size = max(0, min(50, int(request.query_params.get("size", size))))

        #
        # validate parameters
        #
        errors = {}
        if dates_errors:
            errors.update(dates_errors)

        if call_direction_errors:
            errors.update(call_direction_errors)

        # need is_industry_average_request XOR valid practice (valid_practice_id and not practice_errors)
        # can't have both
        if is_industry_averages_request and valid_practice_id:
            error_message = f"{practice_id_parameter_name} or {industry_average_parameter_name} must be provided, but not more than one of them."
            errors.update({practice_id_parameter_name: error_message, industry_average_parameter_name: error_message})
        # have to have at least one
        elif not is_industry_averages_request and not valid_practice_id:
            error_message = f"{practice_id_parameter_name} or {industry_average_parameter_name} must be provided, but not more than one of them."
            errors.update({practice_id_parameter_name: error_message, industry_average_parameter_name: error_message})
        # practice needs to be valid
        elif not is_industry_averages_request and practice_errors:
            errors.update(practice_errors)
        # did they provide a practice at all?
        elif not is_industry_averages_request and not practice_errors and not valid_practice_id:
            errors.update({practice_id_parameter_name: "{practice_id_parameter_name} must be provided"})

        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        #
        # create individual filters from parameters
        #
        dates = dates_info.get("dates")
        start_date_str = dates[0]
        end_date_str = dates[1]
        dates_filter = Q(call_start_time__gte=start_date_str, call_start_time__lte=end_date_str)

        call_direction_filter = Q()
        if valid_call_direction:
            call_direction_filter = Q(call_direction=valid_call_direction)

        #
        # filter and compute
        #

        # handle industry averages
        base_filters = NAEPT_PATIENT_FILTER & dates_filter & call_direction_filter
        if is_industry_averages_request:
            results = self._get_top_mentions(INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER & base_filters, self._RESOURCE_NAME, size, is_industry_averages_request)
            return Response({"results": results})

        # handle practice
        practice = Practice.objects.get(id=valid_practice_id)
        practice_filter = Q(practice__id=valid_practice_id)
        results = self._get_top_mentions(practice_filter & base_filters, self._RESOURCE_NAME, size, is_industry_averages_request)

        # calculate organization averages
        organization_id = practice.organization_id
        if organization_id:
            num_practices = Practice.objects.filter(organization_id=organization_id).count()
            organization_filter = Q(practice__organization_id=organization_id)
            results["organization_averages"] = self._get_top_mentions(
                organization_filter & base_filters, self._RESOURCE_NAME, size, is_industry_averages_request
            )
            results["organization_averages"] = map_nested_objs(obj=results["organization_averages"], func=partial(divide_safely_if_possible, num_practices))
        else:
            results["organization_averages"] = deepcopy(results)

        return Response({"results": results})

    def _get_top_mentions(self, call_filters: Q, resource_name: str, size: int, is_industry_averages_request: bool) -> Dict:
        mentioned_resource_name = f"mentioned_{resource_name}"
        mentioned_resource_keyword = f"{mentioned_resource_name}__keyword"
        count_label = "count"
        non_null_keyword_filter = Q(**{f"{mentioned_resource_keyword}__isnull": False})
        calls_qs = Call.objects.select_related(mentioned_resource_name).filter(call_filters & non_null_keyword_filter)
        top_mentions = calls_qs.values(mentioned_resource_keyword).annotate(count=Count("id")).order_by(f"-{count_label}")[:size]
        top_mentions = [{"keyword": i[mentioned_resource_keyword], count_label: i[count_label]} for i in top_mentions]
        self._normalize_values(top_mentions)
        if is_industry_averages_request:
            num_industry_averages_practices = Practice.objects.filter(INDUSTRY_AVERAGES_PRACTICE_FILTER).count()
            for i in top_mentions:
                i[count_label] = safe_divide(i[count_label], num_industry_averages_practices, should_round=True, round_places=None)

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
