import logging
from collections import Counter
from typing import Dict

from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncHour
from django_pandas.io import read_frame
from rest_framework import status, views
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_breakdown_per_practice,
    calculate_call_count_by_date_and_hour,
    calculate_call_counts,
    calculate_call_counts_per_field,
    calculate_call_counts_per_field_time_series,
    calculate_call_counts_per_user,
    calculate_call_counts_per_user_time_series,
    calculate_call_non_agent_engagement_type_counts,
    convert_count_results,
)
from calls.analytics.intents.field_choices import CallOutcomeTypes
from calls.field_choices import CallDirectionTypes
from calls.models import Call
from calls.validation import (
    get_validated_call_dates,
    get_validated_practice_group_id,
    get_validated_practice_id,
)
from core.models import InsuranceProviderPhoneNumber

# Get an instance of a logger
log = logging.getLogger(__name__)


class InsuranceProviderCallMetricsView(views.APIView):
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

        insurance_provider_phone_number_filter = Q(sip_callee_number__in=InsuranceProviderPhoneNumber.objects.only("phone_number").all())
        all_filters = (
            Q(call_direction=CallDirectionTypes.OUTBOUND)
            & Q(**dates_filter)
            & Q(**practice_filter)
            & Q(**practice_group_filter)
            & insurance_provider_phone_number_filter
        )
        calls_qs = Call.objects.filter(all_filters)

        analytics = {
            "calls_overall": calculate_call_counts(calls_qs),
            "calls_per_user": calculate_call_counts_per_user(calls_qs),
            "calls_per_user_by_date_and_hour": calculate_call_counts_per_user_time_series(calls_qs),
            "non_agent_engagement_types": calculate_call_non_agent_engagement_type_counts(calls_qs),
        }
        analytics.update(**calculate_call_breakdown_per_insurance_provider(calls_qs))

        if practice_group_filter:
            analytics["calls_per_practice"] = calculate_call_breakdown_per_practice(
                calls_qs, practice_group_filter.get("practice__practice_group_id"), analytics["calls_overall"]
            )

        return Response({"results": analytics})


def calculate_call_breakdown_per_insurance_provider(calls_qs: QuerySet) -> Dict:
    data_per_phone_number = calculate_call_counts_per_field(calls_qs, "sip_callee_number")

    # Successes ---
    successes_qs = calls_qs.filter(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS).values("sip_callee_number")
    data_per_phone_number["call_success_total"] = successes_qs.annotate(count=Count("id")).order_by("-count")
    data_per_phone_number["call_success_total"] = convert_count_results(data_per_phone_number["call_success_total"], "sip_callee_number", "count")

    phone_numbers = InsuranceProviderPhoneNumber.objects.select_related("insurance_provider").filter(
        phone_number__in=data_per_phone_number["call_total"].keys()
    )
    insurance_provider_per_phone_number = {ipp.phone_number: ipp.insurance_provider for ipp in phone_numbers}
    num_phone_numbers_per_insurance_provider = Counter(insurance_provider_per_phone_number.values())

    # HEREBEDRAGONS: Insurance Provider name isn't technically unique so there could be fuckery...
    data_per_insurance_provider_name = {}
    for section_name in ("call_total", "call_connected_total", "call_seconds_total", "call_sentiment_counts", "call_success_total"):
        data_per_insurance_provider_name[section_name] = _aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, section_name, "sum"
        )

    data_per_insurance_provider_name["call_on_hold_seconds_average"] = _aggregate_per_insurance_provider_name(
        data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_on_hold_seconds_average", "avg"
    )
    data_per_insurance_provider_name["call_seconds_average"] = _aggregate_per_insurance_provider_name(
        data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_seconds_average", "avg"
    )

    # Success Rate ---
    data_per_insurance_provider_name["call_success_rate"] = dict()
    for k, v in data_per_insurance_provider_name["call_total"].items():
        success_count = data_per_insurance_provider_name["call_success_total"].get(k, None)
        data_per_insurance_provider_name["call_success_rate"][k] = success_count / v if success_count else 0

    return {
        "calls_per_insurance_provider": data_per_insurance_provider_name,
        "calls_per_insurance_provider_by_date_and_hour": calculate_call_breakdown_per_insurance_provider_by_date_and_hour(
            calls_qs, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number
        ),
    }


def calculate_call_breakdown_per_insurance_provider_by_date_and_hour(
    calls_qs: QuerySet, num_phone_numbers_per_insurance_provider: Dict, insurance_provider_per_phone_number: Dict
) -> Dict:
    data_per_phone_number = calculate_call_counts_per_field_time_series(calls_qs, "sip_callee_number")
    data_per_insurance_provider_name = {}

    for section_name in ("call_total", "call_connected_total", "call_seconds_total"):
        data_per_insurance_provider_name[section_name] = _aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, section_name, "sum"
        )

    data_per_insurance_provider_name["call_on_hold_seconds_average"] = _aggregate_per_insurance_provider_name(
        data_per_phone_number,
        num_phone_numbers_per_insurance_provider,
        insurance_provider_per_phone_number,
        "call_on_hold_seconds_average",
        "avg",
    )
    return data_per_insurance_provider_name


def _aggregate_per_insurance_provider_name(
    data_per_phone_number: Dict,
    num_phone_numbers_per_insurance_provider: Dict,
    insurance_provider_per_phone_number: Dict,
    section_name: str,
    calculation: str,
) -> Dict:
    """
    Given data broken down by phone number, aggregate it by insurance provider/name instead
    calculation must be either "sum" or "avg"

    HEREBEDRAGONS: This is fragile and overly complex and works only with very specifically-structured dicts
    """
    data_per_provider = dict()
    is_time_series = False
    for phone_number, value in data_per_phone_number[section_name].items():
        insurance_provider = insurance_provider_per_phone_number[phone_number]
        new_value = value
        existing_value = data_per_provider.get(insurance_provider, None)
        if existing_value:
            if isinstance(existing_value, dict):
                new_value = dict()
                if isinstance(value, list):
                    is_time_series = True
                    value = {d["call_date_hour"]: {k: v for k, v in d.items() if k != "call_date_hour"} for d in value}
                for k, v in existing_value.items():
                    subvalue = value.get(k, None)
                    new_value[k] = v + subvalue if subvalue is not None else v
            else:
                new_value = existing_value + value
        if isinstance(new_value, list):
            is_time_series = True
            new_value = {d["call_date_hour"]: {k: v for k, v in d.items() if k != "call_date_hour"} for d in value}
        data_per_provider[insurance_provider] = new_value

    if calculation == "avg":
        for insurance_provider, v in data_per_provider.items():
            num_phone_numbers = num_phone_numbers_per_insurance_provider[insurance_provider]
            if isinstance(v, dict):
                new_value = dict()
                for subkey, subvalue in v.items():
                    if isinstance(subvalue, dict):
                        for subvalue_key, subvalue_value in subvalue.items():
                            if subvalue_key == "call_date_hour":
                                subvalue[subvalue_key] = subvalue_value
                            else:
                                subvalue[subvalue_key] = subvalue_value / num_phone_numbers
                    else:
                        new_value[subkey] = subvalue / num_phone_numbers
            else:
                new_value = v / num_phone_numbers
            data_per_provider[insurance_provider] = new_value

    if is_time_series:
        for p, value_per_provider in data_per_provider.items():
            data_per_provider[p] = [{"call_date_hour": k, **v} for k, v in value_per_provider.items()]
    return {p.name: v for p, v in data_per_provider.items()}
