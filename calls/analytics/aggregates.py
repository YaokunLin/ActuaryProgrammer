import logging
from datetime import timedelta
from typing import Dict, List, Union

from django.db.models import (
    Aggregate,
    Avg,
    Case,
    CharField,
    Count,
    F,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, ExtractWeekDay, TruncHour
from django_pandas.io import read_frame

from core.models import Practice

# Get an instance of a logger
log = logging.getLogger(__name__)


def calculate_call_counts(calls_qs: QuerySet) -> Dict:
    # get call counts
    analytics = dict(
        calls_qs.aggregate(
            call_total=Count("id"),
            call_connected_total=Count("call_connection", filter=Q(call_connection="connected")),
            call_seconds_total=Sum("duration_seconds"),
            call_seconds_average=Avg("duration_seconds"),
        )
    )

    analytics["call_sentiment_counts"] = calculate_call_sentiments(calls_qs)
    return analytics


def calculate_call_non_agent_engagement_type_counts(calls_qs: QuerySet) -> Dict:
    non_agent_engagement_key = "engaged_in_calls__non_agent_engagement_persona_type"
    non_agent_engagement_qs = calls_qs.values(non_agent_engagement_key).annotate(count=Count(non_agent_engagement_key))

    non_agent_engagement_counts = convert_count_results(non_agent_engagement_qs, non_agent_engagement_key, "count")
    return non_agent_engagement_counts


def annotate_caller_number_with_extension(calls_qs: QuerySet) -> QuerySet:
    """
    Annotates a field "sip_caller_number_with_extension"
    If extension is not blank, the value will be {sip_caller_number}x{sip_caller_extension}
    Else, the value will be {sip_caller_number}
    """
    return calls_qs.annotate(
        sip_caller_number_with_extension=Case(
            When(sip_caller_extension__exact="", then=F("sip_caller_number")),
            default=Concat("sip_caller_number", Value("x"), "sip_caller_extension", output_field=CharField()),
            output_field=CharField(),
        )
    )


def calculate_call_counts_per_user(calls_qs: QuerySet) -> Dict:
    calls_qs = annotate_caller_number_with_extension(calls_qs)
    return calculate_call_counts_per_field(calls_qs, "sip_caller_number_with_extension")


def calculate_call_counts_per_practice(calls_qs: QuerySet) -> Dict:
    return calculate_call_counts_per_field(calls_qs, "practice__name")


def calculate_call_counts_per_field(calls_qs: QuerySet, field_name: str) -> Dict:
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

    analytics["call_on_hold_seconds_average"] = calls_qs.annotate(hold_time_seconds_average=Coalesce(Avg("hold_time_seconds"), Value(timedelta()))).order_by(
        "-hold_time_seconds_average"
    )
    analytics["call_on_hold_seconds_average"] = convert_count_results(analytics["call_on_hold_seconds_average"], field_name, "hold_time_seconds_average")

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


def calculate_call_counts_by_day_of_week(calls_qs: QuerySet) -> Dict:
    day_of_week_mapping = {
        1: "sunday",
        2: "monday",
        3: "tuesday",
        4: "wednesday",
        5: "thursday",
        6: "friday",
        7: "saturday",
    }
    calls_qs = calls_qs.annotate(day_of_week=ExtractWeekDay("call_start_time")).values("day_of_week").annotate(call_total=Count("id")).order_by("day_of_week")
    calls_per_day_of_week = {day_of_week_mapping[d["day_of_week"]]: d["call_total"] for d in calls_qs.all()}
    for day_name in day_of_week_mapping.values():
        if day_name not in calls_per_day_of_week:
            calls_per_day_of_week[day_name] = 0
    return calls_per_day_of_week


def calculate_call_counts_per_user_by_date_and_hour(calls_qs: QuerySet) -> Dict:
    calls_qs = annotate_caller_number_with_extension(calls_qs)
    return calculate_call_counts_per_field_by_date_and_hour(calls_qs, "sip_caller_number_with_extension")


def calculate_call_counts_per_practice_by_date_and_hour(calls_qs: QuerySet) -> Dict:
    return calculate_call_counts_per_field_by_date_and_hour(calls_qs, "practice__name")


def calculate_call_counts_by_date_and_hour(calls_qs: QuerySet) -> Dict:
    call_date_hour_label = "call_date_hour"
    data = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(call_date_hour_label)
        .annotate(call_total=Count("id"))
        .order_by(call_date_hour_label)
    )
    return data.all()


def _calculate_call_values_per_field_by_date_and_hour(
    calls_by_field_name_qs: QuerySet, field_name: str, calculation: Union[Aggregate, Coalesce], calculation_name: str
) -> Dict:
    calculated_value_label = "calculated_value"
    call_date_hour_label = "call_date_hour"
    data = (
        calls_by_field_name_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, call_date_hour_label)
        .annotate(calculated_value=calculation)
        .values(field_name, call_date_hour_label, calculated_value_label)
        .order_by(field_name, call_date_hour_label)
    )
    data = read_frame(data)
    data = data.groupby(field_name)[[call_date_hour_label, calculated_value_label]].apply(lambda x: x.to_dict(orient="records")).to_dict()
    for field_value, value_list in data.items():
        for value_dict in value_list:
            value_dict[calculation_name] = value_dict[calculated_value_label]
            del value_dict[calculated_value_label]
    return data


def calculate_call_count_per_field_by_date_and_hour(calls_by_field_name_qs: QuerySet, field_name: str) -> Dict:
    return _calculate_call_values_per_field_by_date_and_hour(calls_by_field_name_qs, field_name, Count("id"), "call_total")


def calculate_average_hold_time_seconds_per_field_by_date_and_hour(calls_by_field_name_qs: QuerySet, field_name: str) -> Dict:
    return _calculate_call_values_per_field_by_date_and_hour(
        calls_by_field_name_qs, field_name, Coalesce(Avg("hold_time_seconds"), Value(timedelta())), "hold_time_seconds_average"
    )


def calculate_total_call_duration_per_field_by_date_and_hour(calls_by_field_name_qs: QuerySet, field_name: str) -> Dict:
    return _calculate_call_values_per_field_by_date_and_hour(
        calls_by_field_name_qs,
        field_name,
        Sum("duration_seconds"),
        "call_seconds_total",
    )


def calculate_average_call_duration_per_field_by_date_and_hour(calls_by_field_name_qs: QuerySet, field_name: str) -> Dict:
    return _calculate_call_values_per_field_by_date_and_hour(
        calls_by_field_name_qs,
        field_name,
        Avg("duration_seconds"),
        "call_seconds_average",
    )


def calculate_call_sentiment_counts_per_field_by_date_and_hour(calls_by_field_name_qs: QuerySet, field_name: str) -> Dict:
    data = (
        calls_by_field_name_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(field_name, "call_date_hour", "call_sentiments__caller_sentiment_score")
        .annotate(call_sentiment_count=Count("call_sentiments__caller_sentiment_score"))
        .values(field_name, "call_date_hour", "call_sentiments__caller_sentiment_score", "call_sentiment_count")
        .order_by(field_name, "call_date_hour")
    )
    data = read_frame(data)
    return (
        data.groupby(field_name)[["call_date_hour", "call_sentiments__caller_sentiment_score", "call_sentiment_count"]]
        .apply(lambda x: x.to_dict(orient="records"))
        .apply(lambda x: convert_count_results(x, "call_sentiments__caller_sentiment_score", "call_sentiment_count"))
        .to_dict()
    )


def calculate_call_counts_per_field_by_date_and_hour(calls_qs: QuerySet, field_name: str) -> Dict:
    analytics = {}

    calls_qs = calls_qs.values(field_name)

    analytics["call_total"] = calculate_call_count_per_field_by_date_and_hour(calls_qs, field_name)
    analytics["call_connected_total"] = calculate_call_count_per_field_by_date_and_hour(calls_qs.filter(call_connection="connected"), field_name)
    analytics["call_seconds_total"] = calculate_total_call_duration_per_field_by_date_and_hour(calls_qs, field_name)
    analytics["call_seconds_average"] = calculate_average_call_duration_per_field_by_date_and_hour(calls_qs, field_name)
    analytics["call_on_hold_seconds_average"] = calculate_average_hold_time_seconds_per_field_by_date_and_hour(calls_qs, field_name)
    analytics["call_sentiment_counts"] = calculate_call_sentiment_counts_per_field_by_date_and_hour(calls_qs, field_name)

    return analytics


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
    if not qs:
        return {}

    for item_dict in qs:
        new_dict = _create_dict_from_key_values(item_dict, key_with_value_for_key, key_with_value_for_values)
        result.append(new_dict)

    return _merge_list_of_dicts_to_dict(result)


def calculate_call_sentiments(calls_qs: QuerySet) -> Dict:
    call_sentiment_score_key = "call_sentiments__caller_sentiment_score"
    call_sentiment_analytics_qs = calls_qs.values(call_sentiment_score_key).annotate(count=Count(call_sentiment_score_key))

    call_sentiment_counts = convert_count_results(call_sentiment_analytics_qs, call_sentiment_score_key, "count")
    return call_sentiment_counts


def calculate_call_breakdown_per_practice(calls_qs: QuerySet, practice_group_id: str, overall_call_counts_data: Dict) -> Dict:
    per_practice = {}
    per_practice_averages = {}
    call_sentiment_counts = {}
    num_practices = Practice.objects.filter(practice_group_id=practice_group_id).count()
    if num_practices:
        per_practice_averages["call_count"] = overall_call_counts_data["call_total"] / num_practices
        per_practice_averages["call_connected_count"] = overall_call_counts_data["call_connected_total"] / num_practices
        per_practice_averages["call_seconds_total"] = overall_call_counts_data["call_seconds_total"] / num_practices
        per_practice_averages["call_seconds_average"] = overall_call_counts_data["call_seconds_average"] / num_practices

        sentiments_types = ("not_applicable", "positive", "neutral", "negative")
        for sentiment_type in sentiments_types:
            call_sentiment_counts[sentiment_type] = overall_call_counts_data["call_sentiment_counts"].get(sentiment_type, 0) / num_practices

    per_practice_averages["call_sentiment_counts"] = call_sentiment_counts
    per_practice["averages"] = per_practice_averages
    per_practice["per_practice"] = calculate_call_counts_per_practice(calls_qs)
    per_practice["per_practice_by_date_and_hour"] = calculate_call_counts_per_practice_by_date_and_hour(calls_qs)
    return per_practice


def _create_dict_from_key_values(d: Dict, key_with_value_for_key: str, key_with_value_for_value: str) -> Dict:
    """
    Create a new dictionary by using the keys specified to create a new key: value pair. Used typically for QS modification:
        {column_name_1: value_1, column_name_2: value_2}
        to:
        {"value_1": "value_2"}
    """
    return {d[key_with_value_for_key]: d[key_with_value_for_value]}


def _merge_list_of_dicts_to_dict(l: List[Dict]) -> Dict:
    """
    Merges dictionaries together. Doesn't care about stomping on keys that already exist.
    """
    dict_new = {}
    for dict_sub in l:
        dict_new.update(dict_sub)

    return dict_new
