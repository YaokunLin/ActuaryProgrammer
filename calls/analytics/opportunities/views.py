import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Avg, Count, Q, QuerySet, Sum
from django.db.models.functions import Trunc, TruncHour
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
    invalid_error = {param_name: f"Invalid f{param_name}='{practice_id}'"}

    if not practice_id:
        return None, {param_name: "Must include practice id for call analytics."}  # TODO Kyle: Figure if actually out required

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
    invalid_error = {param_name: f"Invalid f{param_name}='{practice_group_id}'"}

    if not practice_group_id:
        return None, {param_name: "Must include practice group id for call analytics."}  # TODO Kyle: Figure if actually out required

    if request.user.is_staff or request.user.is_superuser:
        if PracticeGroup.objects.filter(id=practice_group_id).exists():
            return practice_group_id, None
        return None, invalid_error

    # Can see any practice's resources if you are an assigned agent to a practice
    allowed_practice_group_ids = Agent.objects.filter(user=request.user).values("practice__practice_group__id", flat=True)
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
        if dates_errors:
            errors.update(dates_errors)
        if bool(valid_practice_id) == bool(valid_practice_group_id):
            error_message = "practice__id or practice__group_id must be provided, but not both."
            errors.update({"practice__id": error_message, "practice__group_id": error_message})
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice_filter = {}
        if valid_practice_id:
            practice_filter = {"practice__id": valid_practice_id}

        practice_group_filter = {}
        if valid_practice_group_id:
            practice_group_filter = {"practice_group__id": valid_practice_group_id}

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = {"call_start_time__gte": call_start_time__gte, "call_start_time__lte": call_start_time__lte}

        analytics = get_call_counts_for_outbound(dates_filter, practice_filter, practice_group_filter)

        return Response({"results": analytics})


def get_call_counts_for_outbound(
    dates_filter: Optional[Dict[str, str]], practice_filter: Optional[Dict[str, str]], practice_group_filter: Optional[Dict[str, str]]
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

    # call count per caller (agent) phone number over time
    analytics["calls_per_user_by_date_and_hour"] = calculate_per_user_time_series_call_counts(calls_qs)

    analytics["non_agent_engagement_types"] = calculate_outbound_call_non_agent_engagement_type_counts(calls_qs)

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


def calculate_call_sentiments(calls_qs: QuerySet) -> Dict:
    # Get sentiment counts
    call_sentiment_analytics_qs = calls_qs.values("call_sentiments__caller_sentiment_score").annotate(
        call_sentiment_count=Count("call_sentiments__caller_sentiment_score")
    )

    call_sentiment_counts = {
        sentiment_row["call_sentiments__caller_sentiment_score"]: sentiment_row["call_sentiment_count"] for sentiment_row in call_sentiment_analytics_qs
    }

    return call_sentiment_counts


def calculate_outbound_call_non_agent_engagement_type_counts(calls_qs: QuerySet) -> Dict:
    return calls_qs.values("engaged_in_calls__non_agent_engagement_persona_type").annotate(
        non_agent_engagement_type_count=Count("engaged_in_calls__non_agent_engagement_persona_type")
    )


#
# Call Counts - Per User
#


def calculate_per_user_call_counts(calls_qs: QuerySet) -> Dict:
    analytics = {}

    # group by caller_number
    calls_qs = calls_qs.values("sip_caller_number")

    # calculate and convert

    analytics["call_total"] = calls_qs.annotate(count=Count("id")).order_by("-count")
    analytics["call_total"] = convert_count_results(analytics["call_total"], "sip_caller_number", "count")

    analytics["call_connected_total"] = calls_qs.filter(call_connection="connected").annotate(count=Count("id")).order_by("-count")
    analytics["call_connected_total"] = convert_count_results(analytics["call_connected_total"], "sip_caller_number", "count")

    analytics["call_seconds_total"] = calls_qs.annotate(call_seconds_total=Sum("duration_seconds")).order_by("-call_seconds_total")
    analytics["call_seconds_total"] = convert_count_results(analytics["call_seconds_total"], "sip_caller_number", "call_seconds_total")

    analytics["call_seconds_average"] = calls_qs.annotate(call_seconds_average=Avg("duration_seconds")).order_by("-call_seconds_average")
    analytics["call_seconds_average"] = convert_count_results(analytics["call_seconds_average"], "sip_caller_number", "call_seconds_average")

    analytics["call_sentiment_counts"] = (
        calls_qs.values("sip_caller_number", "call_sentiments__caller_sentiment_score")
        .annotate(call_sentiment_count=Count("call_sentiments__caller_sentiment_score"))
        .values("sip_caller_number", "call_sentiments__caller_sentiment_score", "call_sentiment_count")
        .order_by("sip_caller_number")
    )
    analytics["call_sentiment_counts"] = create_group_of_list_of_dicts_by_key(analytics["call_sentiment_counts"], "sip_caller_number")

    call_sentiment_counts_regrouped = {}
    for grouping, value_list in analytics["call_sentiment_counts"].items():
        log.info(grouping)
        log.info(value_list)
        call_sentiment_counts_regrouped[grouping] = convert_count_results(value_list, "call_sentiments__caller_sentiment_score", "call_sentiment_count")
        log.info(call_sentiment_counts_regrouped[grouping])

    analytics["call_sentiment_counts"] = call_sentiment_counts_regrouped

    return analytics


#
# Call Counts - Per User Time Series
#


def calculate_per_user_time_series_call_counts(calls_qs: QuerySet) -> Dict:
    analytics = {}

    # group by caller_number
    calls_qs = calls_qs.values("sip_caller_number")

    # calculate

    analytics["calls_total"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values("sip_caller_number", "call_date_hour")
        .annotate(call_total=Count("id"))
        .values("sip_caller_number", "call_date_hour", "call_total")
        .order_by("sip_caller_number", "call_date_hour")
    )
    analytics["call_connected_total"] = (
        calls_qs.filter(call_connection="connected")
        .annotate(call_date_hour=TruncHour("call_start_time"))
        .values("sip_caller_number", "call_date_hour")
        .annotate(call_total=Count("id"))
        .values("sip_caller_number", "call_date_hour", "call_total")
        .order_by("sip_caller_number", "call_date_hour")
    )
    analytics["call_seconds_total"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values("sip_caller_number", "call_date_hour")
        .annotate(call_seconds_total=Sum("duration_seconds"))
        .values("sip_caller_number", "call_date_hour", "call_seconds_total")
        .order_by("sip_caller_number", "call_date_hour")
    )
    analytics["call_seconds_average"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values("sip_caller_number", "call_date_hour")
        .annotate(call_seconds_average=Avg("duration_seconds"))
        .values("sip_caller_number", "call_date_hour", "call_seconds_average")
        .order_by("sip_caller_number", "call_date_hour")
    )
    analytics["call_sentiment_counts"] = (
        calls_qs.annotate(call_date_hour=TruncHour("call_start_time"))
        .values("sip_caller_number", "call_date_hour", "call_sentiments__caller_sentiment_score")
        .annotate(call_sentiment_count=Count("call_sentiments__caller_sentiment_score"))
        .values("sip_caller_number", "call_date_hour", "call_sentiments__caller_sentiment_score", "call_sentiment_count")
        .order_by("sip_caller_number", "call_date_hour")
    )

    return analytics


def create_group_of_list_of_dicts_by_key(qs: QuerySet, key_to_group_by: str) -> List[Dict]:
    """
    Pulls up a value from a list of dictionaries to create a higher-level grouping. This is a destructive / mutative operation.
        Input, QS result of:
        [
            {"grouping": "a", "col1": "val_a", "col2": "val"},
            {"grouping": "a", "col1": "val_b", "col2": "val"},
            {"grouping": "a", "col1": "val_c", "col2": "val"},
            {"grouping": "b", "col1": "val_a", "col2": "val"},
            {"grouping": "b", "col1": "val_b", "col2": "val"},
        ]
        to:
        [
            "a": [
                {"col1": "val_a", "col2": "val"},
                {"col1": "val_b", "col2": "val"},
                {"col1": "val_c", "col2": "val"}
            ],
            "b": [
                {"col1": "val_a", "col2": "val"},
                {"col1": "val_b", "col2": "val"}
            ]
        ]
    """
    grouping_dict = defaultdict(list)

    for d in qs:
        grouping = d.pop(key_to_group_by)
        grouping_dict[grouping].append(d)

    return grouping_dict


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
        practice__id = request.query_params.get("practice__id")
        valid_practice, practice_errors = authorize_and_validate_practice_id(request=request)
        dates_info = validate_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = {}
        if valid_practice and practice__id:
            practice_filter = {"practice__id": practice__id}

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
        )
        winback_opportunities_total_qs = new_patient_opportunities_qs.filter(
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE, **dates_filter, **practice_filter
        )
        winback_opportunities_won_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.OUTBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS,
            **dates_filter,
            **practice_filter,
        )
        winback_opportunities_lost_qs = Call.objects.filter(
            call_direction=CallDirectionTypes.OUTBOUND,
            engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT,
            call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE,
            **dates_filter,
            **practice_filter,
        )

        aggregates["new_patient_opportunities_total"] = new_patient_opportunities_qs.count()
        aggregates["winback_opportunities_total"] = winback_opportunities_total_qs.count()
        aggregates["winback_opportunities_won"] = winback_opportunities_won_qs.count()
        aggregates["winback_opportunities_lost"] = winback_opportunities_lost_qs.count()
        aggregates["winback_opportunities_attempted"] = aggregates.get("winback_opportunities_won", 0) + aggregates.get("winback_opportunities_lost", 0)
        aggregates["winback_opportunities_open"] = aggregates.get("winback_opportunities_total", 0) + aggregates.get("winback_opportunities_attempted", 0)

        # display syntactic sugar
        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})


if __name__ == "__main__":

    practice_filter = {"practice__id": "595HFaVZjjjCXfbMBbXzcd"}
    dates_filter = {"call_start_time__gte": "2022-07-05", "call_start_time__lte": "2022-08-16"}

    counts = get_call_counts_for_outbound(dates_filter=dates_filter, practice_filter=practice_filter)
    print(counts)
