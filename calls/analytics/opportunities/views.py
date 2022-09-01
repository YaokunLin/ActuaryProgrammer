import datetime
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, cast

import pandas as pd
from django.db.models import Avg, Count, Q, QuerySet, Sum
from django.db.models.functions import TruncDate, TruncHour, TruncWeek
from django_pandas.io import read_frame
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.intents.field_choices import CallOutcomeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.field_choices import CallDirectionTypes
from calls.models import Call
from calls.validation import validate_call_dates
from core.models import Agent, Practice, PracticeGroup

# Get an instance of a logger
log = logging.getLogger(__name__)


def get_validated_practice_id(request: Request) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    param_name = "practice__id"
    practice_id = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{practice_id}'"}

    if not practice_id:
        return None, None

    if request.user.is_staff or request.user.is_superuser:
        if Practice.objects.filter(id=practice_id).exists():
            return practice_id, None
        return None, invalid_error

    # Can see any practice's resources if you are an assigned agent to a practice
    allowed_practice_ids = Agent.objects.filter(user=request.user).values_list(param_name, flat=True)
    if practice_id not in allowed_practice_ids:
        return None, invalid_error

    return practice_id, None


def get_validated_practice_group_id(request: Request) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    param_name = "practice_group__id"
    practice_group_id = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{practice_group_id}'"}

    if not practice_group_id:
        return None, None

    if request.user.is_staff or request.user.is_superuser:
        if PracticeGroup.objects.filter(id=practice_group_id).exists():
            return practice_group_id, None
        return None, invalid_error

    # Can see any practice's resources if you are an assigned agent to a practice
    allowed_practice_group_ids = Agent.objects.filter(user=request.user).values_list("practice__practice_group__id", flat=True)
    if practice_group_id not in allowed_practice_group_ids:
        return None, {param_name: f"Invalid {param_name}='{practice_group_id}'"}

    return practice_group_id, None


class CallMetricsView(views.APIView):
    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_practice_group_id, practice_group_errors = get_validated_practice_group_id(request=request)
        dates_info = validate_call_dates(query_data=request.query_params)
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

        analytics = get_call_counts_for_outbound(dates_filter, practice_filter, practice_group_filter)

        return Response({"results": analytics})


def get_call_counts_for_outbound(
    dates_filter: Optional[Dict[str, str]],
    practice_filter: Optional[Dict[str, str]],
    practice_group_filter: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    analytics = {}

    # set re-usable filters
    filters = Q(call_direction=CallDirectionTypes.OUTBOUND) & Q(**dates_filter) & Q(**practice_filter) & Q(**practice_group_filter)

    # set re-usable filtered queryset
    calls_qs = Call.objects.filter(filters)

    # perform call counts
    analytics["calls_overall"] = calculate_call_counts(calls_qs)
    analytics["calls_overall"]["call_sentiment_counts"] = calculate_call_sentiments(calls_qs)

    # call counts per caller (agent) phone number
    analytics["calls_per_user"] = calculate_per_user_call_counts(calls_qs)

    # call counts per caller (agent) phone number over time
    analytics["calls_per_user_by_date_and_hour"] = calculate_call_counts_per_user_time_series(calls_qs)

    analytics["non_agent_engagement_types"] = calculate_outbound_call_non_agent_engagement_type_counts(calls_qs)
    # analytics["non_agent_engagement_types"] = convert_count_results(analytics["non_agent_engagement_types"], )

    if practice_group_filter:
        practice_group_id = practice_group_filter.get("practice__practice_group_id")
        per_practice_averages = {}
        call_sentiment_counts = {}
        num_practices = Practice.objects.filter(practice_group_id=practice_group_id).count()

        calls_overall = analytics["calls_overall"]
        per_practice_averages["call_total"] = calls_overall["call_total"] / num_practices
        per_practice_averages["call_connected_total"] = calls_overall["call_connected_total"] / num_practices
        per_practice_averages.update(calculate_call_count_durations_averages_per_practice(calls_qs))

        sentiments_types = ("not_applicable", "positive", "neutral", "negative")
        for sentiment_type in sentiments_types:
            call_sentiment_counts[sentiment_type] = calls_overall["call_sentiment_counts"].get(sentiment_type, 0) / num_practices

        per_practice_averages["call_sentiment_counts"] = call_sentiment_counts
        analytics["per_practice_averages"] = per_practice_averages

    return analytics


#
# Overall Call Counts
#
def calculate_call_counts(calls_qs: QuerySet) -> Dict:
    # get call counts
    count_analytics = calls_qs.aggregate(
        call_total=Count("id"),
        call_connected_total=Count("call_connection", filter=Q(call_connection="connected")),
        call_seconds_total=Sum("duration_seconds"),
        call_seconds_average=Avg("duration_seconds"),
    )

    return count_analytics


def calculate_call_count_durations_averages_per_practice(calls_qs: QuerySet) -> Dict:
    # TODO: Maybe this is unnecessary and we can just do simple math :thnk:
    call_seconds_total = (
        calls_qs.values("practice_id").annotate(sum_duration_sec=Sum("duration_seconds")).aggregate(Avg("sum_duration_sec"))["sum_duration_sec__avg"]
    )
    call_seconds_average = (
        calls_qs.values("practice_id").annotate(avg_duration_sec=Avg("duration_seconds")).aggregate(Avg("avg_duration_sec"))["avg_duration_sec__avg"]
    )

    return {"call_seconds_total": call_seconds_total, "call_seconds_average": call_seconds_average}


def calculate_call_sentiments(calls_qs: QuerySet) -> Dict:
    call_sentiment_score_key = "call_sentiments__caller_sentiment_score"
    call_sentiment_analytics_qs = calls_qs.values(call_sentiment_score_key).annotate(count=Count(call_sentiment_score_key))

    call_sentiment_counts = convert_count_results(call_sentiment_analytics_qs, call_sentiment_score_key, "count")
    return call_sentiment_counts


def calculate_outbound_call_non_agent_engagement_type_counts(calls_qs: QuerySet) -> Dict:
    non_agent_engagement_key = "engaged_in_calls__non_agent_engagement_persona_type"
    non_agent_engagement_qs = calls_qs.values(non_agent_engagement_key).annotate(count=Count(non_agent_engagement_key))

    non_agent_engagement_counts = convert_count_results(non_agent_engagement_qs, non_agent_engagement_key, "count")
    return non_agent_engagement_counts


def _calculate_call_counts_per_field(calls_qs: QuerySet, field_name: str) -> Dict:
    analytics = {}

    # group by field name first
    calls_qs = calls_qs.values(field_name)

    # calculate and convert
    analytics["call_total"] = calls_qs.annotate(count=Count("id")).order_by("-count")
    analytics["call_total"] = convert_count_results(analytics["call_total"], field_name, "count")

    analytics["call_connected_total"] = calls_qs.filter(call_connection="connected").annotate(count=Count("id")).order_by("-count")
    analytics["call_connected_total"] = convert_count_results(analytics["call_connected_total"], field_name, "count")

    analytics["call_seconds_total"] = calls_qs.annotate(call_seconds_total=Sum("duration_seconds")).order_by("-call_seconds_total")
    analytics["call_seconds_total"] = convert_count_results(analytics["call_seconds_total"], field_name, "call_seconds_total")

    analytics["call_seconds_average"] = calls_qs.annotate(call_seconds_average=Avg("duration_seconds")).order_by("-call_seconds_average")
    analytics["call_seconds_average"] = convert_count_results(analytics["call_seconds_average"], field_name, "call_seconds_average")

    analytics["call_sentiment_counts"] = (
        calls_qs.values(field_name, "call_sentiments__caller_sentiment_score")
        .annotate(call_sentiment_count=Count("call_sentiments__caller_sentiment_score"))
        .values(field_name, "call_sentiments__caller_sentiment_score", "call_sentiment_count")
        .order_by(field_name)
    )
    analytics["call_sentiment_counts"] = read_frame(analytics["call_sentiment_counts"])
    analytics["call_sentiment_counts"] = (
        analytics["call_sentiment_counts"]
        .groupby(field_name)[["call_sentiments__caller_sentiment_score", "call_sentiment_count"]]
        .apply(lambda x: x.to_dict(orient="records"))
        .apply(lambda x: convert_count_results(x, "call_sentiments__caller_sentiment_score", "call_sentiment_count"))
        .to_dict()
    )

    return analytics


def calculate_per_practice_call_counts(calls_qs: QuerySet) -> Dict:
    return _calculate_call_counts_per_field(calls_qs, "practice_id")


def calculate_per_user_call_counts(calls_qs: QuerySet) -> Dict:
    return _calculate_call_counts_per_field(calls_qs, "sip_caller_number")


#
# Call Counts - Per Field Time Series
#
def _calculate_call_counts_per_field_time_series(calls_qs: QuerySet, field_name: str) -> Dict:
    analytics = {}

    # group by field name first
    calls_qs = calls_qs.values(field_name)

    # calculate
    analytics["calls_total"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, "call_date_hour")
        .annotate(call_total=Count("id"))
        .values(field_name, "call_date_hour", "call_total")
        .order_by(field_name, "call_date_hour")
    )
    analytics["calls_total"] = read_frame(analytics["calls_total"])
    analytics["calls_total"] = (
        analytics["calls_total"].groupby(field_name)[["call_date_hour", "call_total"]].apply(lambda x: x.to_dict(orient="records")).to_dict()
    )

    analytics["call_connected_total"] = (
        calls_qs.filter(call_connection="connected")
        .annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, "call_date_hour")
        .annotate(call_total=Count("id"))
        .values(field_name, "call_date_hour", "call_total")
        .order_by(field_name, "call_date_hour")
    )
    analytics["call_connected_total"] = read_frame(analytics["call_connected_total"])
    analytics["call_connected_total"] = (
        analytics["call_connected_total"].groupby(field_name)[["call_date_hour", "call_total"]].apply(lambda x: x.to_dict(orient="records")).to_dict()
    )

    analytics["call_seconds_total"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, "call_date_hour")
        .annotate(call_seconds_total=Sum("duration_seconds"))
        .values(field_name, "call_date_hour", "call_seconds_total")
        .order_by(field_name, "call_date_hour")
    )
    analytics["call_seconds_total"] = read_frame(analytics["call_seconds_total"])
    analytics["call_seconds_total"] = (
        analytics["call_seconds_total"].groupby(field_name)[["call_date_hour", "call_seconds_total"]].apply(lambda x: x.to_dict(orient="records")).to_dict()
    )

    analytics["call_seconds_average"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, "call_date_hour")
        .annotate(call_seconds_average=Avg("duration_seconds"))
        .values(field_name, "call_date_hour", "call_seconds_average")
        .order_by(field_name, "call_date_hour")
    )
    analytics["call_seconds_average"] = read_frame(analytics["call_seconds_average"])
    analytics["call_seconds_average"] = (
        analytics["call_seconds_average"].groupby(field_name)[["call_date_hour", "call_seconds_average"]].apply(lambda x: x.to_dict(orient="records")).to_dict()
    )

    analytics["call_sentiment_counts"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, "call_date_hour", "call_sentiments__caller_sentiment_score")
        .annotate(call_sentiment_count=Count("call_sentiments__caller_sentiment_score"))
        .values(field_name, "call_date_hour", "call_sentiments__caller_sentiment_score", "call_sentiment_count")
        .order_by(field_name, "call_date_hour")
    )
    analytics["call_sentiment_counts"] = read_frame(analytics["call_sentiment_counts"])
    analytics["call_sentiment_counts"] = (
        analytics["call_sentiment_counts"]
        .groupby(field_name)[["call_date_hour", "call_sentiment_count"]]
        .apply(lambda x: x.to_dict(orient="records"))
        .to_dict()
    )

    return analytics


def calculate_call_counts_per_user_time_series(calls_qs: QuerySet) -> Dict:
    return _calculate_call_counts_per_field_time_series(calls_qs, "sip_caller_number")


def convert_count_results(qs: QuerySet, key_with_value_for_key: str, key_with_value_for_values: str) -> Dict:
    """
    Convert results from a standard QS result of:
        [
            {column_name_1: value_1, column_name_2: value_2},
            {column_name_1: value_1b, column_name_2: value_2b},
        ]
        to:
        {
            "value_1": "value_2"
            "value_1b": "value_2b"
        }
    """
    result = []

    for item_dict in qs:
        new_dict = create_dict_from_key_values(item_dict, key_with_value_for_key, key_with_value_for_values)
        result.append(new_dict)

    return merge_list_of_dicts_to_dict(result)


def create_dict_from_key_values(d: Dict, key_with_value_for_key: str, key_with_value_for_value: str) -> Dict:
    """
    Create a new dictionary by using the keys specified to create a new key: value pair. Used typically for QS modification:
        {column_name_1: value_1, column_name_2: value_2}
        to:
        {"value_1": "value_2"}
    """
    return {d[key_with_value_for_key]: d[key_with_value_for_value]}


def merge_list_of_dicts_to_dict(l: List[Dict]) -> Dict:
    """
    Merges dictionaries together. Doesn't care about stomping on keys that already exist.
    """
    dict_new = {}
    for dict_sub in l:
        dict_new.update(dict_sub)

    return dict_new


class NewPatientWinbacksView(views.APIView):
    QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME = {"call_start_time__gte": "call_start_time_after", "call_start_time__lte": "call_start_time_before"}

    def get(self, request, format=None):
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        valid_practice_group_id, practice_group_errors = get_validated_practice_group_id(request=request)
        dates_info = validate_call_dates(query_data=request.query_params)
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
        aggregates["new_patient_opportunities_time_series"] = _calculate_new_patient_opportunities_time_series(new_patient_opportunities_qs, dates[0], dates[1])

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

        aggregates["new_patient_opportunities_total"] = new_patient_opportunities_qs.count()
        aggregates["winback_opportunities_total"] = winback_opportunities_total_qs.count()
        aggregates["winback_opportunities_won"] = winback_opportunities_won_qs.count()
        aggregates["winback_opportunities_lost"] = winback_opportunities_lost_qs.count()
        aggregates["winback_opportunities_attempted"] = aggregates.get("winback_opportunities_won", 0) + aggregates.get("winback_opportunities_lost", 0)
        aggregates["winback_opportunities_open"] = aggregates.get("winback_opportunities_total", 0) - aggregates.get("winback_opportunities_attempted", 0)

        if practice_group_filter:
            per_practice_averages = {}
            num_practices = Practice.objects.filter(practice_group_id=valid_practice_group_id).count()
            per_practice_averages["new_patient_opportunities"] = aggregates["new_patient_opportunities_total"] / num_practices
            per_practice_averages["winback_opportunities_total"] = aggregates["winback_opportunities_total"] / num_practices
            per_practice_averages["winback_opportunities_won"] = aggregates["winback_opportunities_won"] / num_practices
            per_practice_averages["winback_opportunities_lost"] = aggregates["winback_opportunities_lost"] / num_practices
            per_practice_averages["winback_opportunities_attempted"] = aggregates["winback_opportunities_attempted"] / num_practices
            per_practice_averages["winback_opportunities_open"] = aggregates["winback_opportunities_open"] / num_practices
            aggregates["per_practice_averages"] = per_practice_averages

        # display syntactic sugar
        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})


def _get_call_count_per_week(qs: QuerySet) -> List[Dict]:
    return list(qs.annotate(date=TruncWeek("call_start_time")).values("date").annotate(value=Count("id")).values("date", "value").order_by("date"))


def _get_call_count_per_day(qs: QuerySet) -> List[Dict]:
    return list(qs.annotate(date=TruncDate("call_start_time")).values("date").annotate(value=Count("id")).values("date", "value").order_by("date"))


def _get_monday(date_str: str, previous: bool = False) -> str:
    """
    If previous is False, returns the next or current Monday
    If previous is True, returns the previous or current Monday
    """
    date_format = "%Y-%m-%d"
    date = datetime.datetime.strptime(date_str, date_format).date()
    if date.weekday():
        date = date + datetime.timedelta(days=-date.weekday(), weeks=-1 if previous else 0)
    return date.strftime(date_format)


def _fill_zeroes(data: List[Dict], start_date: str, end_date: str, frequency_days=1) -> List[Dict]:
    """
    Ensures a given list of timeseries entries contain values for all dates in the expected range.
    Missing values are filled with zero.
    """
    date_field_name = "date"
    value_field_name = "value"
    date_format = "%Y-%m-%d"
    date_range = pd.date_range(start_date, end_date, name=date_field_name, freq=f"{frequency_days}D")
    if not data:
        return [{date_field_name: i.strftime(date_format), value_field_name: 0} for i in date_range]
    data_by_date = {i[date_field_name].strftime(date_format): i[value_field_name] for i in data}
    out = []
    for timestamp in date_range:
        date_str = timestamp.strftime(date_format)
        out.append({date_field_name: date_str, value_field_name: data_by_date.get(date_str, 0)})
    return out


def _calculate_winback_time_series(winbacks_total_qs: QuerySet, winbacks_won_qs: QuerySet, winbacks_lost_qs: QuerySet, start_date: str, end_date: str) -> Dict:
    per_day = {}
    per_week = {}

    def get_winbacks_attempted_breakdown(won: List[Dict], lost: List[Dict]) -> List[Dict]:
        wins_by_date = {i["date"]: i["value"] for i in won}
        lost_by_date = {i["date"]: i["value"] for i in lost}
        all_dates = set(wins_by_date.keys()).union(lost_by_date)
        return [{"date": d, "value": wins_by_date.get(d, 0) + lost_by_date.get(d, 0)} for d in all_dates]

    winbacks_won_per_day = _get_call_count_per_day(winbacks_won_qs)
    winbacks_lost_per_day = _get_call_count_per_day(winbacks_lost_qs)
    per_day["total"] = _fill_zeroes(_get_call_count_per_day(winbacks_total_qs), start_date, end_date)
    per_day["won"] = _fill_zeroes(winbacks_won_per_day, start_date, end_date)
    per_day["lost"] = _fill_zeroes(winbacks_lost_per_day, start_date, end_date)
    per_day["attempted"] = _fill_zeroes(get_winbacks_attempted_breakdown(winbacks_won_per_day, winbacks_lost_per_day), start_date, end_date)

    start_date_week = _get_monday(start_date)
    end_date_week = _get_monday(end_date, previous=True)
    winbacks_won_per_week = _get_call_count_per_week(winbacks_won_qs)
    winbacks_lost_per_week = _get_call_count_per_week(winbacks_lost_qs)
    per_week["total"] = _fill_zeroes(_get_call_count_per_week(winbacks_total_qs), start_date_week, end_date_week, frequency_days=7)
    per_week["won"] = _fill_zeroes(winbacks_won_per_week, start_date_week, end_date_week, frequency_days=7)
    per_week["lost"] = _fill_zeroes(winbacks_lost_per_week, start_date_week, end_date_week, frequency_days=7)
    per_week["attempted"] = _fill_zeroes(
        get_winbacks_attempted_breakdown(winbacks_won_per_week, winbacks_lost_per_week), start_date_week, end_date_week, frequency_days=7
    )

    return {
        "per_day": per_day,
        "per_week": per_week,
    }


def _calculate_new_patient_opportunities_time_series(opportunities_qs: QuerySet, start_date: str, end_date: str) -> Dict:
    per_day = {}
    per_week = {}

    won_qs = opportunities_qs.filter(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS)
    missed_qs = opportunities_qs.filter(went_to_voicemail=True)  # TODO Kyle: This is probably wrong

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

    total_per_day = _get_call_count_per_day(opportunities_qs)
    won_per_day = _get_call_count_per_day(won_qs)
    per_day["total"] = _fill_zeroes(total_per_day, start_date, end_date)
    per_day["won"] = _fill_zeroes(won_per_day, start_date, end_date)
    per_day["missed"] = _fill_zeroes(_get_call_count_per_day(missed_qs), start_date, end_date)
    per_day["conversion_rate"] = _fill_zeroes(get_conversion_rates_breakdown(total_per_day, won_per_day), start_date, end_date)

    start_date_week = _get_monday(start_date)
    end_date_week = _get_monday(end_date, previous=True)
    total_per_week = _get_call_count_per_week(opportunities_qs)
    won_per_week = _get_call_count_per_week(won_qs)
    per_week["total"] = _fill_zeroes(total_per_week, start_date_week, end_date_week, frequency_days=7)
    per_week["won"] = _fill_zeroes(won_per_week, start_date_week, end_date_week, frequency_days=7)
    per_week["missed"] = _fill_zeroes(_get_call_count_per_week(missed_qs), start_date_week, end_date_week, frequency_days=7)
    per_week["conversion_rate"] = _fill_zeroes(get_conversion_rates_breakdown(total_per_week, won_per_week), start_date_week, end_date_week, frequency_days=7)

    return {
        "per_day": per_day,
        "per_week": per_week,
    }
