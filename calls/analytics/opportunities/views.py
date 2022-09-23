import logging
from typing import Any, Dict, List, Optional, Union

from django.db.models import Count, Q, QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_count_opportunities,
    calculate_call_counts,
    calculate_call_counts_and_opportunities_per_user,
    calculate_zero_filled_call_counts_by_day,
    convert_call_counts_to_by_week,
)
from calls.analytics.constants import AVG_VALUE_PER_APPOINTMENT_USD
from calls.analytics.query_filters import (
    FAILURE_FILTER,
    INBOUND_FILTER,
    NEW_PATIENT_FILTER,
    OPPORTUNITIES_FILTER,
    OUTBOUND_FILTER,
    SUCCESS_FILTER,
)
from calls.models import Call
from calls.validation import (
    ALL_FILTER_NAME,
    get_validated_call_dates,
    get_validated_call_direction,
    get_validated_organization_id,
    get_validated_practice_id,
)
from core.models import Practice
from peerlogic.settings import (
    ANALYTICS_CACHE_VARY_ON_HEADERS,
    CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS,
    CACHE_TIME_ANALYTICS_SECONDS,
)

# Get an instance of a logger
log = logging.getLogger(__name__)

REVENUE_PER_WINBACK_USD = 10_000


class CallCountsView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_organization_id, organization_errors = get_validated_organization_id(request=request)
        valid_call_direction, call_direction_errors = get_validated_call_direction(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if organization_errors:
            errors.update(organization_errors)
        if not practice_errors and not organization_errors and bool(valid_practice_id) == bool(valid_organization_id):
            error_message = "practice__id or practice__organization_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__organization_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        organization_filter = {}
        if valid_organization_id:
            organization_filter = {"practice__organization_id": valid_organization_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        # TODO: include filters to REST API for other call directions (Inbound)
        call_direction_filter = {}
        if valid_call_direction:
            call_direction_filter = {"call_direction": valid_call_direction}

        analytics = get_call_counts(dates_filter, practice_filter, organization_filter, call_direction_filter)

        return Response({"results": analytics})


class OpportunitiesView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        calls_qs = self._get_queryset_or_error_response(request, extra_filter=INBOUND_FILTER)
        if isinstance(calls_qs, Response):
            return calls_qs

        opportunities_qs = calls_qs.filter(OPPORTUNITIES_FILTER)
        opportunities_by_outcome = opportunities_qs.values("call_purposes__outcome_results__call_outcome_type").annotate(count=Count("id"))
        d = {r["call_purposes__outcome_results__call_outcome_type"]: r["count"] for r in opportunities_by_outcome}

        total_count = opportunities_qs.count()
        won_count = d.get("success", 0)
        lost_count = d.get("failure", 0)
        n_a_count = total_count - (won_count + lost_count)
        opportunity_counts = {
            "total": total_count,
            "won": won_count,
            "lost": lost_count,
            "not_applicable": n_a_count,
        }
        opportunity_values = {
            "total": total_count * AVG_VALUE_PER_APPOINTMENT_USD,
            "won": won_count * AVG_VALUE_PER_APPOINTMENT_USD,
            "lost": lost_count * AVG_VALUE_PER_APPOINTMENT_USD,
            "not_applicable": n_a_count * AVG_VALUE_PER_APPOINTMENT_USD,
        }
        results = {
            "counts": opportunity_counts,
            "values": opportunity_values,
        }
        return Response(results)

    @staticmethod
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
        return Call.objects.filter(**dates_filter).filter(extra_filter)


def get_call_counts(
    dates_filter: Optional[Dict[str, str]],
    practice_filter: Optional[Dict[str, str]],
    organization_filter: Optional[Dict[str, str]],
    call_direction_filter: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    start_date_str = dates_filter["call_start_time__gte"]
    end_date_str = dates_filter["call_start_time__lte"]

    # set re-usable filters
    filters = Q(**call_direction_filter) & Q(**dates_filter) & Q(**practice_filter) & Q(**organization_filter)

    # set re-usable filtered queryset
    calls_qs = Call.objects.filter(filters)

    analytics = {
        "calls_overall": calculate_call_counts(calls_qs, True),  # perform call counts
        "opportunities": calculate_call_count_opportunities(calls_qs, start_date_str, end_date_str),
        # TODO: PTECH-1240
        # "calls_per_user": calculate_call_counts_per_user(calls_qs),  # call counts per caller (agent) phone number
        # "calls_per_user_by_date_and_hour": calculate_call_counts_per_user_by_date_and_hour(calls_qs),  # call counts per caller (agent) phone number over time
        # "non_agent_engagement_types": calculate_call_non_agent_engagement_type_counts(calls_qs),  # call counts for non agents
    }

    # TODO: PTECH-1240
    # if organization_filter:
    #     analytics["calls_per_practice"] = calculate_call_breakdown_per_practice(
    #         calls_qs, organization_filter.get("practice__organization_id"), analytics["calls_overall"]
    #     )
    return analytics


class OpportunitiesPerUserView(views.APIView):
    QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME = {"call_start_time__gte": "call_start_time_after", "call_start_time__lte": "call_start_time_before"}

    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_organization_id, organization_errors = get_validated_organization_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if organization_errors:
            errors.update(organization_errors)
        if not practice_errors and not organization_errors and bool(valid_practice_id) == bool(valid_organization_id):
            error_message = "practice__id or practice__organization_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__organization_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        filters = Q(**dates_filter) & Q(**practice_filter) & INBOUND_FILTER
        calls_qs = Call.objects.filter(filters)

        aggregates = {
            "agent": calculate_call_counts_and_opportunities_per_user(calls_qs),  # call counts per caller (agent) phone number
        }

        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})


class NewPatientOpportunitiesView(views.APIView):
    QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME = {"call_start_time__gte": "call_start_time_after", "call_start_time__lte": "call_start_time_before"}

    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_organization_id, organization_errors = get_validated_organization_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if organization_errors:
            errors.update(organization_errors)
        if not practice_errors and not organization_errors and bool(valid_practice_id) == bool(valid_organization_id):
            error_message = "practice__id or practice__organization_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__organization_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        organization_filter = {}
        if valid_organization_id:
            organization_filter = {"practice__organization__id": valid_organization_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        calls_qs = Call.objects.filter(**dates_filter, **practice_filter, **organization_filter)
        # aggregate analytics
        aggregates = {}
        new_patient_opportunities_qs = calls_qs.filter(NEW_PATIENT_FILTER & INBOUND_FILTER)
        aggregates["new_patient_opportunities_total"] = new_patient_opportunities_qs.count()
        aggregates["new_patient_opportunities_time_series"] = _calculate_new_patient_opportunities_time_series(new_patient_opportunities_qs, dates[0], dates[1])

        new_patient_opportunities_won_qs = calls_qs.filter(NEW_PATIENT_FILTER & INBOUND_FILTER & SUCCESS_FILTER)
        aggregates["new_patient_opportunities_won_total"] = new_patient_opportunities_won_qs.count()

        new_patient_opportunities_lost_qs = calls_qs.filter(NEW_PATIENT_FILTER & INBOUND_FILTER & FAILURE_FILTER)
        aggregates["new_patient_opportunities_lost_total"] = new_patient_opportunities_lost_qs.count()

        # conversion
        if aggregates["new_patient_opportunities_total"] == 0:  # check for divide by zer0
            aggregates["new_patient_opportunities_conversion_rate_total"] = 0
        else:
            aggregates["new_patient_opportunities_conversion_rate_total"] = (
                aggregates["new_patient_opportunities_won_total"] / aggregates["new_patient_opportunities_total"]
            )

        if organization_filter:
            per_practice_averages = {}
            num_practices = Practice.objects.filter(organization_id=valid_organization_id).count()
            per_practice_averages["new_patient_opportunities"] = aggregates["new_patient_opportunities_total"] / num_practices
            per_practice_averages["new_patient_opportunities_won"] = aggregates["new_patient_opportunities_won_total"] / num_practices
            per_practice_averages["new_patient_opportunities_lost"] = aggregates["new_patient_opportunities_lost_total"] / num_practices
            aggregates["new_patient_opportunities_conversion_rate"] = aggregates["new_patient_opportunities_conversion_rate_total"] / num_practices
            aggregates["per_practice_averages"] = per_practice_averages

        # display syntactic sugar
        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})


class NewPatientWinbacksView(views.APIView):
    QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME = {"call_start_time__gte": "call_start_time_after", "call_start_time__lte": "call_start_time_before"}

    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_organization_id, organization_errors = get_validated_organization_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if organization_errors:
            errors.update(organization_errors)
        if not practice_errors and not organization_errors and bool(valid_practice_id) == bool(valid_organization_id):
            error_message = "practice__id or practice__organization_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__organization_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        organization_filter = {}
        if valid_organization_id:
            organization_filter = {"practice__organization__id": valid_organization_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        calls_qs = Call.objects.filter(**dates_filter, **practice_filter, **organization_filter)

        # aggregate analytics
        aggregates = {}
        winback_opportunities_total_qs = calls_qs.filter(INBOUND_FILTER & NEW_PATIENT_FILTER & FAILURE_FILTER)
        winback_opportunities_won_qs = calls_qs.filter(OUTBOUND_FILTER & NEW_PATIENT_FILTER & SUCCESS_FILTER)
        winback_opportunities_lost_qs = calls_qs.filter(OUTBOUND_FILTER & NEW_PATIENT_FILTER & FAILURE_FILTER)
        aggregates["winback_opportunities_time_series"] = _calculate_winback_time_series(
            winback_opportunities_total_qs, winback_opportunities_won_qs, winback_opportunities_lost_qs, dates[0], dates[1]
        )
        aggregates["winback_opportunities_total"] = winback_opportunities_total_qs.count()
        aggregates["winback_opportunities_won"] = winback_opportunities_won_qs.count()
        aggregates["winback_opportunities_revenue_dollars"] = aggregates["winback_opportunities_won"] * REVENUE_PER_WINBACK_USD
        aggregates["winback_opportunities_lost"] = winback_opportunities_lost_qs.count()
        aggregates["winback_opportunities_attempted"] = aggregates.get("winback_opportunities_won", 0) + aggregates.get("winback_opportunities_lost", 0)
        aggregates["winback_opportunities_open"] = aggregates.get("winback_opportunities_total", 0) - aggregates.get("winback_opportunities_attempted", 0)

        # display syntactic sugar
        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})


def _calculate_winback_time_series(winbacks_total_qs: QuerySet, winbacks_won_qs: QuerySet, winbacks_lost_qs: QuerySet, start_date: str, end_date: str) -> Dict:
    per_day = {}
    per_week = {}

    def get_winbacks_attempted_breakdown(won: List[Dict], lost: List[Dict]) -> List[Dict]:
        wins_by_date = {i["date"]: i["value"] for i in won}
        lost_by_date = {i["date"]: i["value"] for i in lost}
        all_dates = sorted(list(set(wins_by_date.keys()).union(lost_by_date)))
        return [{"date": d, "value": wins_by_date.get(d, 0) + lost_by_date.get(d, 0)} for d in all_dates]

    winbacks_total_per_day = calculate_zero_filled_call_counts_by_day(winbacks_total_qs, start_date, end_date)
    winbacks_won_per_day = calculate_zero_filled_call_counts_by_day(winbacks_won_qs, start_date, end_date)
    winbacks_revenue_per_day = [{"date": d["date"], "value": d["value"] * REVENUE_PER_WINBACK_USD} for d in winbacks_won_per_day]
    winbacks_lost_per_day = calculate_zero_filled_call_counts_by_day(winbacks_lost_qs, start_date, end_date)
    winbacks_attempted_per_day = get_winbacks_attempted_breakdown(winbacks_won_per_day, winbacks_lost_per_day)
    per_day["total"] = winbacks_total_per_day
    per_day["won"] = winbacks_won_per_day
    per_day["revenue_dollars"] = winbacks_revenue_per_day
    per_day["lost"] = winbacks_lost_per_day
    per_day["attempted"] = winbacks_attempted_per_day

    per_week["total"] = convert_call_counts_to_by_week(winbacks_total_per_day)
    per_week["won"] = convert_call_counts_to_by_week(winbacks_won_per_day)
    per_week["revenue_dollars"] = convert_call_counts_to_by_week(winbacks_revenue_per_day)
    per_week["lost"] = convert_call_counts_to_by_week(winbacks_lost_per_day)
    per_week["attempted"] = convert_call_counts_to_by_week(winbacks_attempted_per_day)

    return {
        "per_day": per_day,
        "per_week": per_week,
    }


def _calculate_new_patient_opportunities_time_series(opportunities_qs: QuerySet, start_date: str, end_date: str) -> Dict:
    per_day = {}
    per_week = {}

    won_qs = opportunities_qs.filter(SUCCESS_FILTER)
    lost_qs = opportunities_qs.filter(FAILURE_FILTER)

    def get_conversion_rates_breakdown(total: List[Dict], won: List[Dict]) -> List[Dict]:
        conversion_rates = []
        total_per_date_mapping = {i["date"]: i["value"] for i in total}
        for record in won:
            date = record["date"]
            total_for_date = total_per_date_mapping[date]
            rate = 0
            if total_for_date:
                rate = record["value"] / total_per_date_mapping[date]
            conversion_rates.append({"date": date, "value": rate})
        return conversion_rates

    total_per_day = calculate_zero_filled_call_counts_by_day(opportunities_qs, start_date, end_date)
    won_per_day = calculate_zero_filled_call_counts_by_day(won_qs, start_date, end_date)
    lost_per_day = calculate_zero_filled_call_counts_by_day(lost_qs, start_date, end_date)
    conversion_rate_per_day = get_conversion_rates_breakdown(total_per_day, won_per_day)
    per_day["total"] = total_per_day
    per_day["won"] = won_per_day
    per_day["lost"] = lost_per_day
    per_day["conversion_rate"] = conversion_rate_per_day

    per_week["total"] = convert_call_counts_to_by_week(total_per_day)
    per_week["won"] = convert_call_counts_to_by_week(won_per_day)
    per_week["lost"] = convert_call_counts_to_by_week(lost_per_day)
    per_week["conversion_rate"] = convert_call_counts_to_by_week(conversion_rate_per_day)

    return {
        "per_day": per_day,
        "per_week": per_week,
    }
