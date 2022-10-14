import collections.abc
import datetime
import logging
from datetime import timedelta
from typing import Dict, List, Optional, Union

import pandas as pd
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
from django.db.models.functions import (
    Coalesce,
    Concat,
    ExtractWeekDay,
    TruncDate,
    TruncHour,
)
from django_pandas.io import read_frame

from calls.analytics.intents.field_choices import CallPurposeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.analytics.query_filters import (
    ANSWERED_FILTER,
    CONNECTED_FILTER,
    EXISTING_PATIENT_FILTER,
    FAILURE_FILTER,
    MISSED_FILTER,
    NEW_APPOINTMENT_FILTER,
    NEW_PATIENT_FILTER,
    OPPORTUNITIES_FILTER,
    SUCCESS_FILTER,
    WENT_TO_VOICEMAIL_FILTER,
)
from calls.field_choices import CallDirectionTypes, SentimentTypes
from core.models import Practice

# Get an instance of a logger
log = logging.getLogger(__name__)


def calculate_call_counts(calls_qs: QuerySet, include_by_weekday_breakdown: bool = False) -> Dict:
    analytics = dict(
        calls_qs.aggregate(
            call_total=Count("id"),
            call_connected_total=Count("call_connection", filter=CONNECTED_FILTER),
            call_seconds_total=Sum("duration_seconds"),
            call_seconds_average=Avg("duration_seconds"),
            call_answered_total=Count("id", filter=ANSWERED_FILTER),
            call_voicemail_total=Count("id", filter=WENT_TO_VOICEMAIL_FILTER),
            call_missed_total=Count("id", filter=MISSED_FILTER),
        )
    )

    analytics["call_sentiment_counts"] = calculate_call_sentiments(calls_qs)
    analytics["call_direction_counts"] = calculate_call_directions(calls_qs)
    analytics["call_naept_counts"] = calculate_naept(calls_qs)
    analytics["call_purpose_counts"] = calculate_purpose(calls_qs)

    if include_by_weekday_breakdown:
        analytics["calls_by_weekday"] = {
            "call_total": convert_to_call_counts_only(
                convert_to_call_counts_and_durations_by_weekday(get_call_counts_and_durations_by_weekday_and_hour(calls_qs))
            ),
            "call_connected_total": convert_to_call_counts_only(
                convert_to_call_counts_and_durations_by_weekday(get_call_counts_and_durations_by_weekday_and_hour(calls_qs.filter(CONNECTED_FILTER)))
            ),
            "call_answered_total": convert_to_call_counts_only(
                convert_to_call_counts_and_durations_by_weekday(get_call_counts_and_durations_by_weekday_and_hour(calls_qs.filter(ANSWERED_FILTER)))
            ),
            "call_voicemail_total": convert_to_call_counts_only(
                convert_to_call_counts_and_durations_by_weekday(get_call_counts_and_durations_by_weekday_and_hour(calls_qs.filter(WENT_TO_VOICEMAIL_FILTER)))
            ),
            "call_missed_total": convert_to_call_counts_only(
                convert_to_call_counts_and_durations_by_weekday(get_call_counts_and_durations_by_weekday_and_hour(calls_qs.filter(MISSED_FILTER)))
            ),
        }

    return analytics


def calculate_call_count_opportunities(calls_qs: QuerySet, start_date_str: str, end_date_str: str) -> Dict:
    opportunities_total_qs = calls_qs.filter(OPPORTUNITIES_FILTER)
    opportunities_existing_patient_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & EXISTING_PATIENT_FILTER)
    opportunities_new_patient_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & NEW_PATIENT_FILTER)

    opportunities_won_total_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & SUCCESS_FILTER & (EXISTING_PATIENT_FILTER | NEW_PATIENT_FILTER))
    opportunities_won_existing_patient_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & SUCCESS_FILTER & EXISTING_PATIENT_FILTER)
    opportunities_won_new_patient_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & SUCCESS_FILTER & NEW_PATIENT_FILTER)

    opportunities_lost_total_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & FAILURE_FILTER & (EXISTING_PATIENT_FILTER | NEW_PATIENT_FILTER))
    opportunities_lost_existing_patient_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & FAILURE_FILTER & EXISTING_PATIENT_FILTER)
    opportunities_lost_new_patient_qs = calls_qs.filter(NEW_APPOINTMENT_FILTER & FAILURE_FILTER & NEW_PATIENT_FILTER)

    def get_conversion_rates_breakdown(total: List[Dict], won: List[Dict]) -> List[Dict]:
        conversion_rates = []
        total_per_date_mapping = {i["date"]: i["value"] for i in total}
        for record in won:
            date = record["date"]
            total_for_date = total_per_date_mapping[date]
            rate = 0
            if total_for_date:
                rate = safe_divide(record["value"], total_per_date_mapping[date])
            conversion_rates.append({"date": date, "value": rate})
        return conversion_rates

    total_by_day = calculate_zero_filled_call_counts_by_day(opportunities_total_qs, start_date_str, end_date_str)
    existing_patient_by_day = calculate_zero_filled_call_counts_by_day(opportunities_existing_patient_qs, start_date_str, end_date_str)
    new_patient_by_day = calculate_zero_filled_call_counts_by_day(opportunities_new_patient_qs, start_date_str, end_date_str)

    opportunities = {
        "total": opportunities_total_qs.count(),
        "existing": opportunities_existing_patient_qs.count(),
        "new": opportunities_new_patient_qs.count(),
    }
    opportunities["total_by_week"] = {
        "total": convert_call_counts_to_by_week(total_by_day),
        "existing": convert_call_counts_to_by_week(existing_patient_by_day),
        "new": convert_call_counts_to_by_week(new_patient_by_day),
    }
    opportunities["total_by_month"] = {
        "total": convert_call_counts_to_by_month(total_by_day),
        "existing": convert_call_counts_to_by_month(existing_patient_by_day),
        "new": convert_call_counts_to_by_month(new_patient_by_day),
    }
    opportunities["won"] = {
        "total": opportunities_won_total_qs.count(),
        "existing": opportunities_won_existing_patient_qs.count(),
        "new": opportunities_won_new_patient_qs.count(),
    }
    won_by_day_total = calculate_zero_filled_call_counts_by_day(opportunities_won_total_qs, start_date_str, end_date_str)
    won_by_day_existing_patient = calculate_zero_filled_call_counts_by_day(opportunities_won_existing_patient_qs, start_date_str, end_date_str)
    won_by_day_new_patient = calculate_zero_filled_call_counts_by_day(opportunities_won_new_patient_qs, start_date_str, end_date_str)
    opportunities["won_by_week"] = {
        "total": convert_call_counts_to_by_week(won_by_day_total),
        "existing": convert_call_counts_to_by_week(won_by_day_existing_patient),
        "new": convert_call_counts_to_by_week(won_by_day_new_patient),
    }
    opportunities["won_by_month"] = {
        "total": convert_call_counts_to_by_month(won_by_day_total),
        "existing": convert_call_counts_to_by_month(won_by_day_existing_patient),
        "new": convert_call_counts_to_by_month(won_by_day_new_patient),
    }
    opportunities["conversion_rate"] = {
        "total": safe_divide(opportunities["won"]["total"], opportunities["total"]),
        "existing": safe_divide(opportunities["won"]["existing"], opportunities["existing"]),
        "new": safe_divide(opportunities["won"]["new"], opportunities["new"]),
    }
    opportunities["conversion_rate_by_week"] = {
        "total": get_conversion_rates_breakdown(opportunities["total_by_week"]["total"], opportunities["won_by_week"]["total"]),
        "existing": get_conversion_rates_breakdown(opportunities["total_by_week"]["existing"], opportunities["won_by_week"]["existing"]),
        "new": get_conversion_rates_breakdown(opportunities["total_by_week"]["new"], opportunities["won_by_week"]["new"]),
    }
    opportunities["conversion_rate_by_month"] = {
        "total": get_conversion_rates_breakdown(opportunities["total_by_month"]["total"], opportunities["won_by_month"]["total"]),
        "existing": get_conversion_rates_breakdown(opportunities["total_by_month"]["existing"], opportunities["won_by_month"]["existing"]),
        "new": get_conversion_rates_breakdown(opportunities["total_by_month"]["new"], opportunities["won_by_month"]["new"]),
    }

    opportunities["lost"] = {
        "total": opportunities_lost_total_qs.count(),
        "existing": opportunities_lost_existing_patient_qs.count(),
        "new": opportunities_lost_new_patient_qs.count(),
    }
    lost_by_day_total = calculate_zero_filled_call_counts_by_day(opportunities_lost_total_qs, start_date_str, end_date_str)
    lost_by_day_existing_patient = calculate_zero_filled_call_counts_by_day(opportunities_lost_existing_patient_qs, start_date_str, end_date_str)
    lost_by_day_new_patient = calculate_zero_filled_call_counts_by_day(opportunities_lost_new_patient_qs, start_date_str, end_date_str)
    opportunities["lost_by_week"] = {
        "total": convert_call_counts_to_by_week(lost_by_day_total),
        "existing": convert_call_counts_to_by_week(lost_by_day_existing_patient),
        "new": convert_call_counts_to_by_week(lost_by_day_new_patient),
    }
    opportunities["lost_by_month"] = {
        "total": convert_call_counts_to_by_month(lost_by_day_total),
        "existing": convert_call_counts_to_by_month(lost_by_day_existing_patient),
        "new": convert_call_counts_to_by_month(lost_by_day_new_patient),
    }

    return opportunities


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
    annotation = _get_annotation_for_phone_number_with_extension("sip_caller")
    return calls_qs.annotate(**annotation)


def annotate_callee_number_with_extension(calls_qs: QuerySet) -> QuerySet:
    """
    Annotates a field "sip_callee_number_with_extension"
    If extension is not blank, the value will be {sip_callee_number}x{sip_callee_extension}
    Else, the value will be {sip_callee_number}
    """
    annotation = _get_annotation_for_phone_number_with_extension("sip_callee")
    return calls_qs.annotate(**annotation)


def _get_annotation_for_phone_number_with_extension(root_phone_number_field_name: str) -> Dict:
    """
    Will generate an annotation based upon the root of the field name for a phone number. Assumes that the phone number and extension field follow our standard
    conventions

    root_phone_number_field_name: root of the phone number field name, not the full field name itself. e.g. "sip_callee", "sip_caller"
    """
    extension_field_name = f"{root_phone_number_field_name}_extension"
    phone_number_field_name = f"{root_phone_number_field_name}_number"
    phone_with_extension_field_name = f"{phone_number_field_name}_with_extension"

    extension_blank_filter = Q(**{extension_field_name: ""})
    annotation = {
        phone_with_extension_field_name: Case(
            When(extension_blank_filter, then=F(phone_number_field_name)),
            default=Concat(phone_number_field_name, Value("x"), extension_field_name, output_field=CharField()),
            output_field=CharField(),
        )
    }

    return annotation


def calculate_call_counts_and_opportunities_per_user(calls_qs: QuerySet) -> Dict:
    # set field_name for all calculations
    phone_with_extension_field_name = "sip_callee_number_with_extension"
    field_name = phone_with_extension_field_name

    # root annotated queryset for all subsequent calculations
    calls_qs = annotate_callee_number_with_extension(calls_qs)

    # get distinct sip_caller_number_with_extensions first to form the basis of our return and subsequent joins, includes location / practice
    user_and_practice_qs = calls_qs.distinct(field_name).values(
        field_name, "sip_callee_number", "sip_callee_extension", "practice__name", "practice__address_us_state", "practice__created_at"
    )

    # call totals
    call_total_qs = calls_qs.values(field_name).annotate(call_count=Count("id")).values(field_name, "call_count")
    call_missed_qs = (
        calls_qs.filter(call_connection="missed").values(field_name).annotate(call_missed_count=Count("id")).values(field_name, "call_missed_count")
    )

    opportunities_total_qs = (
        calls_qs.filter(NEW_APPOINTMENT_FILTER & (EXISTING_PATIENT_FILTER | NEW_PATIENT_FILTER))
        .values(field_name)
        .annotate(opportunities_total_count=Count("id"))
        .values(field_name, "opportunities_total_count")
    )
    opportunities_won_qs = (
        calls_qs.filter(NEW_APPOINTMENT_FILTER & SUCCESS_FILTER & (EXISTING_PATIENT_FILTER | NEW_PATIENT_FILTER))
        .values(field_name)
        .annotate(opportunities_won_count=Count("id"))
        .values(field_name, "opportunities_won_count")
    )

    # create dataframes for crunching
    user_and_practice_info = read_frame(user_and_practice_qs)
    call_count = read_frame(call_total_qs)
    call_missed_count = read_frame(call_missed_qs)
    call_opportunities_total_count = read_frame(opportunities_total_qs)
    call_opportunities_won_count = read_frame(opportunities_won_qs)

    # assemble
    frame_to_return = user_and_practice_info
    frames_to_join = [call_count, call_missed_count, call_opportunities_total_count, call_opportunities_won_count]
    for frame in frames_to_join:
        frame_to_return = frame_to_return.merge(frame, how="left", on=field_name)  # merges are a sql-like join. retain left-most rows, always

    frame_to_return.fillna(0, inplace=True)  # dictionaries may not intersect, this creates non-serializable nan values, replace nan with 0 and do it in-place

    # compute derived values
    frame_to_return["opportunities_open_count"] = frame_to_return["opportunities_total_count"] - frame_to_return["opportunities_won_count"]

    return frame_to_return.to_dict(orient="records")


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
    weekday_label = "weekday"
    weekday_mapping = {
        1: "sunday",
        2: "monday",
        3: "tuesday",
        4: "wednesday",
        5: "thursday",
        6: "friday",
        7: "saturday",
    }
    calls_qs = calls_qs.annotate(weekday=ExtractWeekDay("call_start_time")).values(weekday_label).annotate(call_total=Count("id")).order_by(weekday_label)
    calls_per_day_of_week = {weekday_mapping[d[weekday_label]]: d["call_total"] for d in calls_qs.all()}
    for day_name in weekday_mapping.values():
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
    data = {k: 0 for k in SentimentTypes}
    call_sentiment_score_key = "call_sentiments__caller_sentiment_score"
    call_sentiment_analytics_qs = calls_qs.values(call_sentiment_score_key).annotate(count=Count(call_sentiment_score_key))

    data.update(convert_count_results(call_sentiment_analytics_qs, call_sentiment_score_key, "count"))
    if None in data:
        data[SentimentTypes.NOT_APPLICABLE.value] = (data[SentimentTypes.NOT_APPLICABLE.value] or 0) + (data[None] or 0)
        del data[None]
    return data


def calculate_call_directions(calls_qs: QuerySet) -> Dict:
    data = {k: 0 for k in CallDirectionTypes}
    data.update(convert_count_results(calls_qs.values("call_direction").annotate(count=Count("id")), "call_direction", "count"))
    return data


def calculate_naept(calls_qs: QuerySet) -> Dict:
    data = {k: 0 for k in NonAgentEngagementPersonaTypes}
    data.update(
        convert_count_results(
            calls_qs.values("engaged_in_calls__non_agent_engagement_persona_type").annotate(count=Count("id")),
            "engaged_in_calls__non_agent_engagement_persona_type",
            "count",
        )
    )
    if None in data:
        data["not_applicable"] = data[None]
        del data[None]
    return data


def calculate_purpose(calls_qs: QuerySet) -> Dict:
    data = {k: 0 for k in CallPurposeTypes}
    data.update(
        convert_count_results(calls_qs.values("call_purposes__call_purpose_type").annotate(count=Count("id")), "call_purposes__call_purpose_type", "count")
    )
    if None in data:
        data["not_applicable"] = data[None]
        del data[None]
    return data


def calculate_call_breakdown_per_practice(calls_qs: QuerySet, organization_id: str, overall_call_counts_data: Dict) -> Dict:
    per_practice = {}
    per_practice_averages = {}
    call_sentiment_counts = {}
    num_practices = Practice.objects.filter(organization_id=organization_id).count()
    per_practice_averages["call_count"] = safe_divide(overall_call_counts_data["call_total"], num_practices)
    per_practice_averages["call_connected_count"] = safe_divide(overall_call_counts_data["call_connected_total"], num_practices)
    per_practice_averages["call_seconds_total"] = safe_divide(overall_call_counts_data["call_seconds_total"], num_practices)
    per_practice_averages["call_seconds_average"] = safe_divide(overall_call_counts_data["call_seconds_average"], num_practices)

    sentiments_types = ("not_applicable", "positive", "neutral", "negative")
    for sentiment_type in sentiments_types:
        call_sentiment_counts[sentiment_type] = safe_divide(overall_call_counts_data["call_sentiment_counts"].get(sentiment_type, 0), num_practices)

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


SUNDAY = "sunday"
MONDAY = "monday"
TUESDAY = "tuesday"
WEDNESDAY = "wednesday"
THURSDAY = "thursday"
FRIDAY = "friday"
SATURDAY = "saturday"


def get_call_counts_and_durations_by_weekday_and_hour(calls_qs: QuerySet) -> Dict:
    weekday_by_index = {
        0: MONDAY,
        1: TUESDAY,
        2: WEDNESDAY,
        3: THURSDAY,
        4: FRIDAY,
        5: SATURDAY,
        6: SUNDAY,
    }
    call_date_hour_label = "call_date_hour"
    call_count_label = "call_count"
    total_call_duration_label = "total_call_duration_seconds"
    total_hold_duration_label = "total_hold_duration_seconds"
    average_call_duration_label = "average_call_duration_seconds"
    average_hold_duration_label = "average_hold_duration_seconds"
    efficiency_label = "efficiency"
    per_hour_label = "per_hour"
    weekday_label = "weekday"

    # Group data by date_and_hour
    data = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values(call_date_hour_label)
        .annotate(
            call_count=Count("id"),
            total_call_duration_seconds=Sum("duration_seconds"),
            total_hold_duration_seconds=Coalesce(Sum("hold_time_seconds"), Value(timedelta())),
        )
        .order_by(call_date_hour_label)
    ).all()

    # Convert data by date_and_hour into data_by_weekday_and_hour
    data_by_weekday_and_hour = {
        MONDAY: {per_hour_label: {}, weekday_label: MONDAY},
        TUESDAY: {per_hour_label: {}, weekday_label: TUESDAY},
        WEDNESDAY: {per_hour_label: {}, weekday_label: WEDNESDAY},
        THURSDAY: {per_hour_label: {}, weekday_label: THURSDAY},
        FRIDAY: {per_hour_label: {}, weekday_label: FRIDAY},
        SATURDAY: {per_hour_label: {}, weekday_label: SATURDAY},
        SUNDAY: {per_hour_label: {}, weekday_label: SUNDAY},
    }
    for data_for_hour in data:
        data_datetime = data_for_hour[call_date_hour_label]
        weekday = weekday_by_index[data_datetime.weekday()]
        hour = data_datetime.hour
        existing_data = data_by_weekday_and_hour[weekday][per_hour_label].get(hour, {})
        data_by_weekday_and_hour[weekday][per_hour_label][hour] = {
            call_count_label: existing_data.get(call_count_label, 0) + data_for_hour[call_count_label],
            total_call_duration_label: existing_data.get(total_call_duration_label, timedelta()) + data_for_hour[total_call_duration_label],
            total_hold_duration_label: existing_data.get(total_hold_duration_label, timedelta()) + data_for_hour[total_hold_duration_label],
        }

    for data_for_weekday in data_by_weekday_and_hour.values():
        for i in range(1, 25):  # 1-24 hours in a day
            if i not in data_for_weekday[per_hour_label]:
                data_for_weekday[per_hour_label][i] = {
                    call_count_label: 0,
                    total_call_duration_label: timedelta(),
                    total_hold_duration_label: timedelta(),
                    average_call_duration_label: timedelta(),
                    average_hold_duration_label: timedelta(),
                }

        for hour, data_for_hour in data_for_weekday[per_hour_label].items():
            # Per hour, calculate efficiency, average call duration and average hold duration
            call_count = data_for_hour[call_count_label]
            total_seconds = data_for_hour[total_call_duration_label].total_seconds()
            data_for_hour[efficiency_label] = safe_divide(data_for_hour[call_count_label], total_seconds)
            data_for_hour[average_call_duration_label] = safe_divide(data_for_hour[total_call_duration_label].total_seconds(), call_count)
            data_for_hour[average_hold_duration_label] = safe_divide(data_for_hour[total_hold_duration_label].total_seconds(), call_count)

    return data_by_weekday_and_hour


def convert_to_call_counts_and_durations_by_weekday(call_counts_and_durations_by_weekday_and_hour: Dict) -> Dict:
    call_count_label = "call_count"
    total_call_duration_label = "total_call_duration_seconds"
    average_call_duration_label = "average_call_duration_seconds"

    data_by_weekday = {}
    for weekday, data_for_current_weekday in call_counts_and_durations_by_weekday_and_hour.items():
        for data_for_current_hour in data_for_current_weekday["per_hour"].values():
            data = data_by_weekday.setdefault(
                weekday,
                {
                    call_count_label: 0,
                    total_call_duration_label: timedelta(),
                },
            )
            data[call_count_label] = data[call_count_label] + data_for_current_hour[call_count_label]
            data[total_call_duration_label] = data[total_call_duration_label] + data_for_current_hour[total_call_duration_label]

    for d in data_by_weekday.values():
        call_count = d[call_count_label]
        d[average_call_duration_label] = safe_divide(d[total_call_duration_label], call_count)

    return data_by_weekday


def convert_to_call_counts_and_durations_by_hour(call_counts_and_durations_by_weekday_and_hour: Dict) -> Dict:
    call_count_label = "call_count"
    total_call_duration_label = "total_call_duration_seconds"
    average_call_duration_label = "average_call_duration_seconds"

    data_by_hour = {}
    for data_for_current_weekday in call_counts_and_durations_by_weekday_and_hour.values():
        for hour, data_for_current_hour in data_for_current_weekday["per_hour"].items():
            data = data_by_hour.setdefault(
                hour,
                {
                    call_count_label: 0,
                    total_call_duration_label: timedelta(),
                },
            )
            data[call_count_label] = data[call_count_label] + data_for_current_hour[call_count_label]
            data[total_call_duration_label] = data[total_call_duration_label] + data_for_current_hour[total_call_duration_label]

    for d in data_by_hour.values():
        call_count = d[call_count_label]
        d[average_call_duration_label] = safe_divide(d[total_call_duration_label], call_count)

    return data_by_hour


def convert_to_call_counts_only(call_counts_and_durations: Dict) -> Dict:
    """
    Convert data by hour or data by weekday to only contain call counts
    """
    return {k: v["call_count"] for k, v in call_counts_and_durations.items()}


def calculate_zero_filled_call_counts_by_day(calls_qs: QuerySet, start_date: str, end_date: str, field_to_count: str = "id") -> List[Dict]:
    data = list(
        calls_qs.annotate(date=TruncDate("call_start_time")).values("date").annotate(value=Count(field_to_count)).values("date", "value").order_by("date")
    )
    if not data:
        return []

    date_range = pd.date_range(start_date, end_date, name="date")
    data = pd.DataFrame(data).set_index("date").reindex(date_range, fill_value=0).reset_index()
    data = data.to_dict("records")
    for i in data:
        i["date"] = i["date"].strftime("%Y-%m-%d")
    return data


def convert_call_counts_to_by_week(data_by_day: List[Dict]) -> List[Dict]:
    date_format = "%Y-%m-%d"
    if not data_by_day:
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

    day_of_week = datetime.datetime.strptime(data_by_day[0]["date"], date_format).weekday()
    df = pd.DataFrame(data_by_day)
    df["date"] = df["date"].astype("datetime64[ns]")

    weekly_data = df.resample(f"W-{day_of_week_mapping[day_of_week]}", label="left", closed="left", on="date").sum().reset_index().sort_values(by="date")
    weekly_data = weekly_data.to_dict("records")
    for i in weekly_data:
        i["date"] = i["date"].strftime(date_format)
    return weekly_data


def convert_call_counts_to_by_month(data_by_day: List[Dict]) -> List[Dict]:
    date_format = "%Y-%m-%d"
    if not data_by_day:
        return []

    df = pd.DataFrame(data_by_day)
    df["date"] = df["date"].astype("datetime64[ns]")

    monthly_data = df.resample("MS", on="date").sum().reset_index().sort_values(by="date")
    monthly_data = monthly_data.to_dict("records")
    for i in monthly_data:
        i["date"] = i["date"].strftime(date_format)
    return monthly_data


def safe_divide(dividend: int, divisor: int, default: int = 0, should_round: bool = True, round_places: Optional[int] = 2) -> Union[int, float]:
    """
    Divides, falling back to the provided default if the divisor is falsy.
    Also rounds by default to 2 places if the result is a float.
    """
    result = divisor and dividend / divisor or default
    if should_round:
        result = round_if_float(result, round_places)
    return result


def round_if_float(number: Union[int, float], round_places: Optional[int] = 2) -> Union[int, float]:
    if isinstance(number, float):
        if number.is_integer():
            return int(number)
        return round(number, round_places)
    return number


def map_nested_objs(obj, func):
    """
    Maps the provides function against all values in the nested object (dictionary and lists). It will recursively follow all sub-dicitionaries and lists to an
    arbitrary depth.
    """
    if isinstance(obj, collections.abc.Mapping):
        return {k: map_nested_objs(v, func) for k, v in obj.items()}
    if isinstance(obj, list):
        return [map_nested_objs(i, func) for i in obj]

    return func(obj)


def divide_safely_if_possible(divisor, dividend):
    """
    Attempt to divide the object by the divisor. If its possible the division occurs, otherwise return the number.
    This division is safe and avoid division by zero.
    This operates on anything that responds to division and not just integers and floats.
    """
    try:
        return safe_divide(dividend, divisor)
    except Exception:
        return dividend
