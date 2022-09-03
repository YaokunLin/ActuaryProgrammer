import logging
from typing import Dict, List

from django.db.models import (
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
from django.db.models.functions import Concat, TruncHour
from django_pandas.io import read_frame

# Get an instance of a logger
log = logging.getLogger(__name__)


def calculate_call_counts(calls_qs: QuerySet) -> Dict:
    # get call counts
    count_analytics = calls_qs.aggregate(
        call_total=Count("id"),
        call_connected_total=Count("call_connection", filter=Q(call_connection="connected")),
        call_seconds_total=Sum("duration_seconds"),
        call_seconds_average=Avg("duration_seconds"),
    )

    return count_analytics


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


def calculate_per_user_call_counts(calls_qs: QuerySet) -> Dict:
    analytics = {}

    field_name = "sip_caller_number_with_extension"
    calls_qs = annotate_caller_number_with_extension(calls_qs)

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


def calculate_per_user_call_counts_time_series(calls_qs: QuerySet) -> Dict:
    analytics = {}

    field_name = "sip_caller_number_with_extension"
    calls_qs = annotate_caller_number_with_extension(calls_qs)
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
        return result

    for item_dict in qs:
        new_dict = _create_dict_from_key_values(item_dict, key_with_value_for_key, key_with_value_for_values)
        result.append(new_dict)

    return _merge_list_of_dicts_to_dict(result)


def calculate_call_sentiments(calls_qs: QuerySet) -> Dict:
    call_sentiment_score_key = "call_sentiments__caller_sentiment_score"
    call_sentiment_analytics_qs = calls_qs.values(call_sentiment_score_key).annotate(count=Count(call_sentiment_score_key))

    call_sentiment_counts = convert_count_results(call_sentiment_analytics_qs, call_sentiment_score_key, "count")
    return call_sentiment_counts


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
