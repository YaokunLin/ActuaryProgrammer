import datetime
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncDate
from rest_framework import status, views
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_breakdown_per_practice,
    calculate_call_count_opportunities,
    calculate_call_counts,
    calculate_call_counts_per_user,
    calculate_call_counts_per_user_by_date_and_hour,
    calculate_call_non_agent_engagement_type_counts,
)
from calls.analytics.intents.field_choices import CallOutcomeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.field_choices import CallDirectionTypes
from calls.models import Call
from calls.validation import (
    ALL_FILTER_NAME,
    get_validated_call_dates,
    get_validated_call_direction,
    get_validated_practice_group_id,
    get_validated_practice_id,
)
from core.models import Practice

# Get an instance of a logger
log = logging.getLogger(__name__)

REVENUE_PER_WINBACK_USD = 10_000


class CallMetricsView(views.APIView):
    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_practice_group_id, practice_group_errors = get_validated_practice_group_id(request=request)
        valid_call_direction, call_direction_errors = get_validated_call_direction(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if practice_group_errors:
            errors.update(practice_group_errors)
        if not practice_errors and not practice_group_errors and bool(valid_practice_id) == bool(valid_practice_group_id):
            error_message = "practice__id or practice__group_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__group_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        practice_group_filter = {}
        if valid_practice_group_id:
            practice_group_filter = {"practice__practice_group_id": valid_practice_group_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        # TODO: include filters to REST API for other call directions (Inbound)
        call_direction_filter = {}
        if valid_call_direction == ALL_FILTER_NAME:
            call_direction_filter = {}  # stating explicitly even though it is initialized above
        elif valid_call_direction:
            call_direction_filter = {"call_direction": valid_call_direction}
        else:
            # TODO: Default to no filter after dependency is removed
            {"call_direction": CallDirectionTypes.OUTBOUND}

        analytics = get_call_counts(dates_filter, practice_filter, practice_group_filter, call_direction_filter)

        return Response({"results": analytics})


def get_call_counts(
    dates_filter: Optional[Dict[str, str]],
    practice_filter: Optional[Dict[str, str]],
    practice_group_filter: Optional[Dict[str, str]],
    call_direction_filter: Optional[Dict[str, str]],
) -> Dict[str, Any]:

    # set re-usable filters
    filters = Q(**call_direction_filter) & Q(**dates_filter) & Q(**practice_filter) & Q(**practice_group_filter)

    # set re-usable filtered queryset
    calls_qs = Call.objects.filter(filters)

    analytics = {
        "opportunities": calculate_call_count_opportunities(calls_qs),
        "calls_overall": calculate_call_counts(calls_qs),  # perform call counts
        # TODO: PTECH-1240
        # "calls_per_user": calculate_call_counts_per_user(calls_qs),  # call counts per caller (agent) phone number
        # "calls_per_user_by_date_and_hour": calculate_call_counts_per_user_by_date_and_hour(calls_qs),  # call counts per caller (agent) phone number over time
        "non_agent_engagement_types": calculate_call_non_agent_engagement_type_counts(calls_qs),  # call counts for non agents
    }

    if practice_group_filter:
        analytics["calls_per_practice"] = calculate_call_breakdown_per_practice(
            calls_qs, practice_group_filter.get("practice__practice_group_id"), analytics["calls_overall"]
        )
    return analytics


class NewPatientOpportunitiesView(views.APIView):
    QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME = {"call_start_time__gte": "call_start_time_after", "call_start_time__lte": "call_start_time_before"}

    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_practice_group_id, practice_group_errors = get_validated_practice_group_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if practice_group_errors:
            errors.update(practice_group_errors)
        if not practice_errors and not practice_group_errors and bool(valid_practice_id) == bool(valid_practice_group_id):
            error_message = "practice__id or practice__group_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__group_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        practice_group_filter = {}
        if valid_practice_group_id:
            practice_group_filter = {"practice__practice_group__id": valid_practice_group_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        # aggregate analytics
        aggregates = {}
        new_patient_opportunities_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.INBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            **dates_filter,
            **practice_filter,
            **practice_group_filter,
        )
        aggregates["new_patient_opportunities_total"] = new_patient_opportunities_qs.count()
        aggregates["new_patient_opportunities_time_series"] = _calculate_new_patient_opportunities_time_series(new_patient_opportunities_qs, dates[0], dates[1])

        new_patient_opportunities_won_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.INBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS,
            **dates_filter,
            **practice_filter,
            **practice_group_filter,
        )
        aggregates["new_patient_opportunities_won_total"] = new_patient_opportunities_won_qs.count()

        new_patient_opportunities_lost_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.INBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE,
            **dates_filter,
            **practice_filter,
            **practice_group_filter,
        )
        aggregates["new_patient_opportunities_lost_total"] = new_patient_opportunities_lost_qs.count()

        # conversion
        aggregates["new_patient_opportunities_conversion_rate_total"] = (
            aggregates["new_patient_opportunities_won_total"] / aggregates["new_patient_opportunities_total"]
        )

        # New pt conversion (use absolutes on the frontend)

        if practice_group_filter:
            per_practice_averages = {}
            num_practices = Practice.objects.filter(practice_group_id=valid_practice_group_id).count()
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

    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_practice_group_id, practice_group_errors = get_validated_practice_group_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if practice_group_errors:
            errors.update(practice_group_errors)
        if not practice_errors and not practice_group_errors and bool(valid_practice_id) == bool(valid_practice_group_id):
            error_message = "practice__id or practice__group_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__group_id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        practice_group_filter = {}
        if valid_practice_group_id:
            practice_group_filter = {"practice__practice_group__id": valid_practice_group_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        # aggregate analytics
        aggregates = {}
        new_patient_opportunities_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.INBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            **dates_filter,
            **practice_filter,
            **practice_group_filter,
        )

        winback_opportunities_total_qs = new_patient_opportunities_qs.filter(
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE, **dates_filter, **practice_filter, **practice_group_filter
        )
        winback_opportunities_won_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.OUTBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS,
            **dates_filter,
            **practice_filter,
            **practice_group_filter,
        )
        winback_opportunities_lost_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.OUTBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE,
            **dates_filter,
            **practice_filter,
            **practice_group_filter,
        )
        aggregates["winback_opportunities_time_series"] = _calculate_winback_time_series(
            winback_opportunities_total_qs, winback_opportunities_won_qs, winback_opportunities_lost_qs, dates[0], dates[1]
        )
        aggregates["winback_opportunities_total"] = winback_opportunities_total_qs.count()
        aggregates["winback_opportunities_won"] = winback_opportunities_won_qs.count()
        aggregates["winback_opportunities_revenue_dollars"] = aggregates["winback_opportunities_won"] * REVENUE_PER_WINBACK_USD
        aggregates["winback_opportunities_lost"] = winback_opportunities_lost_qs.count()
        aggregates["winback_opportunities_attempted"] = aggregates.get("winback_opportunities_won", 0) + aggregates.get("winback_opportunities_lost", 0)
        aggregates["winback_opportunities_open"] = aggregates.get("winback_opportunities_total", 0) - aggregates.get("winback_opportunities_attempted", 0)

        if practice_group_filter:
            num_practices = Practice.objects.filter(practice_group_id=valid_practice_group_id).count()
            aggregates["per_practice_averages"] = {
                "winback_opportunities_total": aggregates["winback_opportunities_total"] / num_practices,
                "winback_opportunities_won": aggregates["winback_opportunities_won"] / num_practices,
                "winback_opportunities_revenue": aggregates["winback_opportunities_revenue"] / num_practices,
                "winback_opportunities_lost": aggregates["winback_opportunities_lost"] / num_practices,
                "winback_opportunities_attempted": aggregates["winback_opportunities_attempted"] / num_practices,
                "winback_opportunities_open": aggregates["winback_opportunities_open"] / num_practices,
            }

        # display syntactic sugar
        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})


def _get_zero_filled_call_counts_per_day(calls_qs: QuerySet, start_date: str, end_date: str) -> List[Dict]:
    data = list(calls_qs.annotate(date=TruncDate("call_start_time")).values("date").annotate(value=Count("id")).values("date", "value").order_by("date"))
    if not data:
        return []

    date_range = pd.date_range(start_date, end_date, name="date")
    data = pd.DataFrame(data).set_index("date").reindex(date_range, fill_value=0).reset_index()
    data = data.to_dict("records")
    for i in data:
        i["date"] = i["date"].strftime("%Y-%m-%d")
    return data


def _convert_daily_to_weekly(data: List[Dict]) -> List[Dict]:
    date_format = "%Y-%m-%d"
    if not data:
        return []

    # https://pandas.pydata.org/docs/user_guide/timeseries.html#anchored-offsets
    day_of_week_mapping = {
        0: "MON",
        1: "TUE",
        2: "WED",
        3: "THU",
        4: "FRI",
        5: "SAT",
        6: "SUN",
    }

    day_of_week = datetime.datetime.strptime(data[0]["date"], date_format).weekday()
    df = pd.DataFrame(data)
    df["date"] = df["date"].astype("datetime64[ns]")

    weekly_data = df.resample(f"W-{day_of_week_mapping[day_of_week]}", label="left", closed="left", on="date").sum().reset_index().sort_values(by="date")
    weekly_data = weekly_data.to_dict("records")
    for i in weekly_data:
        i["date"] = i["date"].strftime(date_format)
    return weekly_data


def _calculate_winback_time_series(winbacks_total_qs: QuerySet, winbacks_won_qs: QuerySet, winbacks_lost_qs: QuerySet, start_date: str, end_date: str) -> Dict:
    per_day = {}
    per_week = {}

    def get_winbacks_attempted_breakdown(won: List[Dict], lost: List[Dict]) -> List[Dict]:
        wins_by_date = {i["date"]: i["value"] for i in won}
        lost_by_date = {i["date"]: i["value"] for i in lost}
        all_dates = sorted(list(set(wins_by_date.keys()).union(lost_by_date)))
        return [{"date": d, "value": wins_by_date.get(d, 0) + lost_by_date.get(d, 0)} for d in all_dates]

    winbacks_total_per_day = _get_zero_filled_call_counts_per_day(winbacks_total_qs, start_date, end_date)
    winbacks_won_per_day = _get_zero_filled_call_counts_per_day(winbacks_won_qs, start_date, end_date)
    winbacks_revenue_per_day = [{"date": d["date"], "value": d["value"] * REVENUE_PER_WINBACK_USD} for d in winbacks_won_per_day]
    winbacks_lost_per_day = _get_zero_filled_call_counts_per_day(winbacks_lost_qs, start_date, end_date)
    winbacks_attempted_per_day = get_winbacks_attempted_breakdown(winbacks_won_per_day, winbacks_lost_per_day)
    per_day["total"] = winbacks_total_per_day
    per_day["won"] = winbacks_won_per_day
    per_day["revenue_dollars"] = winbacks_revenue_per_day
    per_day["lost"] = winbacks_lost_per_day
    per_day["attempted"] = winbacks_attempted_per_day

    per_week["total"] = _convert_daily_to_weekly(winbacks_total_per_day)
    per_week["won"] = _convert_daily_to_weekly(winbacks_won_per_day)
    per_week["revenue_dollars"] = _convert_daily_to_weekly(winbacks_revenue_per_day)
    per_week["lost"] = _convert_daily_to_weekly(winbacks_lost_per_day)
    per_week["attempted"] = _convert_daily_to_weekly(winbacks_attempted_per_day)

    return {
        "per_day": per_day,
        "per_week": per_week,
    }


def _calculate_new_patient_opportunities_time_series(opportunities_qs: QuerySet, start_date: str, end_date: str) -> Dict:
    per_day = {}
    per_week = {}

    won_qs = opportunities_qs.filter(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS)
    lost_qs = opportunities_qs.filter(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE)

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

    total_per_day = _get_zero_filled_call_counts_per_day(opportunities_qs, start_date, end_date)
    won_per_day = _get_zero_filled_call_counts_per_day(won_qs, start_date, end_date)
    lost_per_day = _get_zero_filled_call_counts_per_day(lost_qs, start_date, end_date)
    conversion_rate_per_day = get_conversion_rates_breakdown(total_per_day, won_per_day)
    per_day["total"] = total_per_day
    per_day["won"] = won_per_day
    per_day["lost"] = lost_per_day
    per_day["conversion_rate"] = conversion_rate_per_day

    per_week["total"] = _convert_daily_to_weekly(total_per_day)
    per_week["won"] = _convert_daily_to_weekly(won_per_day)
    per_week["lost"] = _convert_daily_to_weekly(lost_per_day)
    per_week["conversion_rate"] = _convert_daily_to_weekly(conversion_rate_per_day)

    return {
        "per_day": per_day,
        "per_week": per_week,
    }
