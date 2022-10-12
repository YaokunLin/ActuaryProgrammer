import logging
from collections import Counter
from copy import deepcopy
from datetime import timedelta
from typing import Dict, Optional, Tuple

from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from numpy import percentile
from rest_framework import status, views
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_counts,
    calculate_call_counts_per_field,
    convert_to_call_counts_and_durations_by_hour,
    convert_to_call_counts_and_durations_by_weekday,
    get_call_counts_and_durations_by_weekday_and_hour,
    round_if_float,
    safe_divide,
)
from calls.analytics.query_filters import (
    INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER,
    INDUSTRY_AVERAGES_PRACTICE_FILTER,
    OUTBOUND_FILTER,
    get_insurance_provider_callee_number_filter,
)
from calls.models import Call
from calls.validation import (
    get_validated_call_dates,
    get_validated_insurance_provider,
    get_validated_practice_id,
)
from core.models import InsuranceProviderPhoneNumber, Practice
from peerlogic.settings import (
    ANALYTICS_CACHE_VARY_ON_HEADERS,
    CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS,
    CACHE_TIME_ANALYTICS_SECONDS,
)

# Get an instance of a logger
log = logging.getLogger(__name__)

# Dict key constants
_AVERAGE_CALL_DURATION_LABEL = "average_call_duration_seconds"
_CALLS_BY_HOUR_LABEL = "calls_by_hour"
_CALLS_BY_WEEKDAY_LABEL = "calls_by_weekday"
_CALLS_OVERALL_LABEL = "calls_overall"
_CALL_COUNT_LABEL = "call_count"
_EFFICIENCY_LABEL = "efficiency"
_HIGHEST_EFFICIENCY_LABEL = "highest_efficiency"
_HOUR_LABEL = "hour"
_MOST_EFFICIENT_HOUR_LABEL = "most_efficient_hour"
_MOST_POPULAR_HOUR_CALL_COUNT_LABEL = "most_popular_hour_call_count"
_MOST_POPULAR_HOUR_LABEL = "most_popular_hour"
_MOST_POPULAR_WEEKDAY_AND_HOUR_LABEL = "most_popular_weekday_and_hour"
_ORGANIZATION_AVERAGES_LABEL = "organization_averages"
_PER_HOUR_LABEL = "per_hour"
_TOTAL_CALL_DURATION_LABEL = "total_call_duration_seconds"
_WEEKDAY_LABEL = "weekday"


class InsuranceProviderInteractionsView(views.APIView):

    # HEREBEDRAGONS: The following variables greatly affect the data that is returned
    #   These values were chosen after a fair bit of trial & error against production data.
    CALL_DURATION_MINIMUM_SECONDS = 60
    CALL_PER_HOUR_PERCENTILE_BY_WEEKDAY_HOUR = 60
    CALL_PER_HOUR_PERCENTILE_BY_HOUR = 70
    LOOKBACK_DAYS = 365

    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        insurance_provider = get_validated_insurance_provider(request)

        num_industry_averages_practices = Practice.objects.filter(INDUSTRY_AVERAGES_PRACTICE_FILTER).count()

        all_filters = (
            OUTBOUND_FILTER
            & Q(call_start_time__gte=timezone.now() - timedelta(days=self.LOOKBACK_DAYS))
            & Q(duration_seconds__gte=timedelta(seconds=self.CALL_DURATION_MINIMUM_SECONDS))
            & INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER
        )
        if insurance_provider:
            all_filters = all_filters & Q(sip_callee_number__in=insurance_provider.insuranceproviderphonenumber_set.only("phone_number"))
        calls_qs = Call.objects.filter(all_filters).all()

        response_data = {}
        if calls_qs:
            data_by_weekday_and_hour = get_call_counts_and_durations_by_weekday_and_hour(calls_qs)
            best_weekday_and_hour_to_call = _get_best_weekday_and_hour_to_call(data_by_weekday_and_hour)

            data_by_weekday, data_by_hour, hour_extremes = _get_weekday_and_hour_breakdowns(data_by_weekday_and_hour, num_industry_averages_practices)
            response_data[_CALLS_BY_WEEKDAY_LABEL] = data_by_weekday
            response_data[_CALLS_BY_HOUR_LABEL] = data_by_hour

            if insurance_provider:
                if best_weekday_and_hour_to_call:
                    response_data["best_weekday_and_hour_to_call"] = best_weekday_and_hour_to_call
                if hour_extremes:
                    response_data.update(hour_extremes)

        if not response_data:
            return Response(
                {"error": f"Insufficient data to calculate best call day and time for {insurance_provider.name}"}, status=status.HTTP_204_NO_CONTENT
            )

        return Response(response_data)


class InsuranceProviderCallMetricsView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        insurance_provider = get_validated_insurance_provider(request)
        valid_practice_id, practice_errors = get_validated_practice_id(request=request)
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice_filter = Q(practice__id=valid_practice_id)
        practice = Practice.objects.get(id=valid_practice_id)

        # date filters
        dates = dates_info.get("dates")
        dates_filter = Q(call_start_time__gte=dates[0], call_start_time__lte=dates[1])

        if insurance_provider:
            insurance_provider_phone_number_filter = Q(sip_callee_number__in=insurance_provider.insuranceproviderphonenumber_set.only("phone_number"))
        else:
            insurance_provider_phone_number_filter = get_insurance_provider_callee_number_filter()

        non_practice_filters = OUTBOUND_FILTER & dates_filter & insurance_provider_phone_number_filter
        calls_qs = Call.objects.filter(non_practice_filters & practice_filter)

        data_by_weekday_and_hour = get_call_counts_and_durations_by_weekday_and_hour(calls_qs)
        data_by_weekday, data_by_hour, hour_extremes = _get_weekday_and_hour_breakdowns(data_by_weekday_and_hour)

        response_data = {
            _MOST_POPULAR_WEEKDAY_AND_HOUR_LABEL: self._get_most_popular_weekday_and_hour(data_by_weekday_and_hour),
            _CALLS_OVERALL_LABEL: calculate_call_counts(calls_qs),
            _CALLS_BY_WEEKDAY_LABEL: data_by_weekday,
            _CALLS_BY_HOUR_LABEL: data_by_hour,
        }
        if hour_extremes:
            response_data.update(hour_extremes)
        if calls_qs:
            response_data.update(**self.calculate_call_breakdown_per_insurance_provider(calls_qs))

        if practice.organization_id:
            num_practices = Practice.objects.filter(organization_id=practice.organization_id).count()
            if num_practices == 1:
                response_data[_ORGANIZATION_AVERAGES_LABEL] = deepcopy(response_data)
            else:
                organization_filter = Q(practice__organization_id=practice.organization_id)
                calls_qs = Call.objects.filter(non_practice_filters & organization_filter)
                data_by_weekday_and_hour = get_call_counts_and_durations_by_weekday_and_hour(calls_qs)
                data_by_weekday, data_by_hour, hour_extremes = _get_weekday_and_hour_breakdowns(data_by_weekday_and_hour, num_practices)
                organization_data = {
                    _MOST_POPULAR_WEEKDAY_AND_HOUR_LABEL: self._get_most_popular_weekday_and_hour(data_by_weekday_and_hour),
                    _CALLS_OVERALL_LABEL: calculate_call_counts(calls_qs),
                    _CALLS_BY_WEEKDAY_LABEL: data_by_weekday,
                    _CALLS_BY_HOUR_LABEL: data_by_hour,
                }
                organization_data.update(hour_extremes)
                if calls_qs:
                    organization_data.update(**self.calculate_call_breakdown_per_insurance_provider(calls_qs))
                response_data[_ORGANIZATION_AVERAGES_LABEL] = organization_data
        else:
            response_data[_ORGANIZATION_AVERAGES_LABEL] = deepcopy(response_data)

        return Response(response_data)

    def calculate_call_breakdown_per_insurance_provider(self, calls_qs: QuerySet) -> Dict:
        data_per_phone_number = calculate_call_counts_per_field(calls_qs, "sip_callee_number")

        phone_numbers = InsuranceProviderPhoneNumber.objects.select_related("insurance_provider").filter(
            phone_number__in=data_per_phone_number["call_total"].keys()
        )
        insurance_provider_per_phone_number = {ipp.phone_number: ipp.insurance_provider for ipp in phone_numbers}
        num_phone_numbers_per_insurance_provider = Counter(insurance_provider_per_phone_number.values())

        # HEREBEDRAGONS: Insurance Provider name isn't technically unique so there could be fuckery...
        data_per_insurance_provider_name = {}
        for section_name in ("call_total", "call_connected_total", "call_seconds_total", "call_sentiment_counts"):
            data_per_insurance_provider_name[section_name] = self._aggregate_per_insurance_provider_name(
                data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, section_name, "sum"
            )

        data_per_insurance_provider_name["call_on_hold_seconds_average"] = self._aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_on_hold_seconds_average", "avg"
        )
        data_per_insurance_provider_name["call_seconds_average"] = self._aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_seconds_average", "avg"
        )

        return {
            "calls_per_insurance_provider": data_per_insurance_provider_name,
        }

    @staticmethod
    def _aggregate_per_insurance_provider_name(
        data_per_phone_number: Dict,
        num_phone_numbers_per_insurance_provider: Dict,
        insurance_provider_per_phone_number: Dict,
        section_name: str,
        calculation: str,
        is_time_series_breakdown: bool = False,
    ) -> Dict:
        """
        Given data broken down by phone number, aggregate it by insurance provider/name instead
        calculation must be either "sum" or "avg"

        HEREBEDRAGONS: This is fragile and overly complex and works only with very specifically-structured dicts
        """
        data_per_provider = dict()
        for phone_number, value in data_per_phone_number[section_name].items():
            insurance_provider = insurance_provider_per_phone_number[phone_number]
            new_value = value
            existing_value = data_per_provider.get(insurance_provider, None)
            if existing_value:
                if isinstance(existing_value, dict):
                    new_value = dict()
                    if is_time_series_breakdown:
                        value = {d["call_date_hour"]: {k: v for k, v in d.items() if k != "call_date_hour"} for d in value}
                    for k, v in existing_value.items():
                        subvalue = value.get(k, None)
                        new_value[k] = v + subvalue if subvalue is not None else v
                else:
                    new_value = existing_value + value
            if is_time_series_breakdown:
                new_value = {d["call_date_hour"]: {k: v for k, v in d.items() if k != "call_date_hour"} for d in value}
            data_per_provider[insurance_provider] = new_value

        if calculation == "avg":
            for insurance_provider, v in data_per_provider.items():
                num_phone_numbers = num_phone_numbers_per_insurance_provider[insurance_provider]
                if isinstance(v, dict):
                    new_value = dict()
                    for subkey, subvalue in v.items():
                        if is_time_series_breakdown:
                            for subvalue_key, subvalue_value in subvalue.items():
                                subvalue[subvalue_key] = safe_divide(subvalue_value, num_phone_numbers)
                            new_value[subkey] = subvalue
                        else:
                            new_value[subkey] = safe_divide(subvalue, num_phone_numbers)
                else:
                    new_value = safe_divide(v, num_phone_numbers)
                data_per_provider[insurance_provider] = new_value

        if is_time_series_breakdown:
            for p, value_per_provider in data_per_provider.items():
                data_per_provider[p] = [{"call_date_hour": k, **v} for k, v in value_per_provider.items()]

        return {p.name: v for p, v in data_per_provider.items()}

    @staticmethod
    def _get_most_popular_weekday_and_hour(data_by_weekday_and_hour: Dict) -> Dict:
        top_day = None
        top_hour = None
        top_day_hour_call_count = 0
        top_day_hour_call_count_average_duration_seconds = None
        for day, data_by_weekday in data_by_weekday_and_hour.items():
            for hour, data_by_hour in data_by_weekday[_PER_HOUR_LABEL].items():
                if data_by_hour[_CALL_COUNT_LABEL] > top_day_hour_call_count:
                    top_hour = hour
                    top_day = day
                    top_day_hour_call_count = data_by_hour[_CALL_COUNT_LABEL]
                    top_day_hour_call_count_average_duration_seconds = data_by_hour[_AVERAGE_CALL_DURATION_LABEL]
        return {
            _WEEKDAY_LABEL: top_day,
            _HOUR_LABEL: top_hour,
            _CALL_COUNT_LABEL: top_day_hour_call_count,
            _AVERAGE_CALL_DURATION_LABEL: top_day_hour_call_count_average_duration_seconds,
        }


def _annotate_efficiency_and_popular_times(data_by_weekday_and_hour: Dict, call_count_cutoff: int = 0) -> None:
    for data_for_weekday in data_by_weekday_and_hour.values():
        # For each day, get the hour with the greatest efficiency which also has >= call_count_cutoff calls made in that hour
        # Store the data about that hour on the day
        d = [
            {_EFFICIENCY_LABEL: v[_EFFICIENCY_LABEL], _HOUR_LABEL: k, _CALL_COUNT_LABEL: v[_CALL_COUNT_LABEL]}
            for k, v in data_for_weekday[_PER_HOUR_LABEL].items()
            if v[_CALL_COUNT_LABEL] >= call_count_cutoff
        ]
        data_per_hour_by_efficiency = sorted(d, key=lambda x: x[_EFFICIENCY_LABEL])
        if data_per_hour_by_efficiency:
            data_for_weekday[_MOST_EFFICIENT_HOUR_LABEL] = data_per_hour_by_efficiency[-1][_HOUR_LABEL]
            data_for_weekday[_HIGHEST_EFFICIENCY_LABEL] = data_per_hour_by_efficiency[-1][_EFFICIENCY_LABEL]
        data_per_hour_by_count = sorted(d, key=lambda x: x[_CALL_COUNT_LABEL])
        if data_per_hour_by_count:
            most_popular_call_count = data_per_hour_by_count[-1][_CALL_COUNT_LABEL]
            if most_popular_call_count:
                data_for_weekday[_MOST_POPULAR_HOUR_LABEL] = data_per_hour_by_count[-1][_HOUR_LABEL]
                data_for_weekday[_MOST_POPULAR_HOUR_CALL_COUNT_LABEL] = most_popular_call_count
            else:
                data_for_weekday[_MOST_POPULAR_HOUR_LABEL] = None
                data_for_weekday[_MOST_POPULAR_HOUR_CALL_COUNT_LABEL] = None


def _get_best_weekday_and_hour_to_call(data_by_weekday_and_hour: Dict) -> Optional[Dict]:
    call_counts_all_hours = []
    for data_for_weekday in data_by_weekday_and_hour.values():
        call_counts_all_hours.extend([d[_CALL_COUNT_LABEL] for d in data_for_weekday[_PER_HOUR_LABEL].values()])
    call_count_cutoff = percentile(call_counts_all_hours, InsuranceProviderInteractionsView.CALL_PER_HOUR_PERCENTILE_BY_WEEKDAY_HOUR)

    _annotate_efficiency_and_popular_times(data_by_weekday_and_hour, call_count_cutoff)

    # Now, sort the days by the one with the highest per-hour efficiency
    days_by_efficient_hours = sorted([d for d in data_by_weekday_and_hour.values()], key=lambda x: x.get(_HIGHEST_EFFICIENCY_LABEL, 0))
    most_efficient_day = days_by_efficient_hours[-1]

    # If we have a day/hour with the highest efficiency which also has a non-zero efficiency, we have a winner!
    if most_efficient_day and most_efficient_day.get(_HIGHEST_EFFICIENCY_LABEL):
        # Return the day, hour and average duration for that time period
        most_efficient_weekday = most_efficient_day[_WEEKDAY_LABEL]
        most_efficient_hour = most_efficient_day[_MOST_EFFICIENT_HOUR_LABEL]
        most_efficient_hour_data = data_by_weekday_and_hour[most_efficient_weekday][_PER_HOUR_LABEL][most_efficient_hour]
        average_duration_at_most_efficient_day_hour = safe_divide(
            most_efficient_hour_data[_TOTAL_CALL_DURATION_LABEL], most_efficient_hour_data[_CALL_COUNT_LABEL]
        )
        return_data = {
            _WEEKDAY_LABEL: most_efficient_weekday,
            _HOUR_LABEL: most_efficient_hour,
            _AVERAGE_CALL_DURATION_LABEL: average_duration_at_most_efficient_day_hour,
        }
        return return_data

    # No good answers based on data, do not suggest
    return None


def _get_weekday_and_hour_breakdowns(data_by_weekday_and_hour: Dict, count_divisor: int = 1) -> Tuple[Dict, Dict, Dict]:
    _annotate_efficiency_and_popular_times(data_by_weekday_and_hour, False)
    data_by_weekday = convert_to_call_counts_and_durations_by_weekday(data_by_weekday_and_hour)
    total_calls = sum(d[_CALL_COUNT_LABEL] for d in data_by_weekday.values())
    for weekday, data in data_by_weekday.items():
        analyzed_weekday_data = data_by_weekday_and_hour[weekday]
        data_by_weekday[weekday] = {
            _CALL_COUNT_LABEL: safe_divide(data[_CALL_COUNT_LABEL], count_divisor),
            "percentage_of_weekly_calls": round_if_float(safe_divide(data[_CALL_COUNT_LABEL], total_calls) * 100),
            _AVERAGE_CALL_DURATION_LABEL: data[_AVERAGE_CALL_DURATION_LABEL],
            _MOST_POPULAR_HOUR_LABEL: analyzed_weekday_data[_MOST_POPULAR_HOUR_LABEL],
            _MOST_POPULAR_HOUR_CALL_COUNT_LABEL: safe_divide(analyzed_weekday_data[_MOST_POPULAR_HOUR_CALL_COUNT_LABEL] or 0, count_divisor),
        }

    data_by_hour = convert_to_call_counts_and_durations_by_hour(data_by_weekday_and_hour)
    data_by_hour = {
        k: {_CALL_COUNT_LABEL: safe_divide(v[_CALL_COUNT_LABEL], count_divisor), _AVERAGE_CALL_DURATION_LABEL: v[_AVERAGE_CALL_DURATION_LABEL]}
        for k, v in data_by_hour.items()
    }
    hour_extremes = _get_worst_and_best_hour_to_call(data_by_hour)
    return data_by_weekday, data_by_hour, hour_extremes


def _get_worst_and_best_hour_to_call(data_by_hour: Dict) -> Optional[Dict]:
    if len(data_by_hour) < 2:
        return None  # Not much insight here if no data or if best == worst

    call_counts_all_hours = [d[_CALL_COUNT_LABEL] for d in data_by_hour.values()]
    call_count_cutoff = percentile(call_counts_all_hours, InsuranceProviderInteractionsView.CALL_PER_HOUR_PERCENTILE_BY_HOUR)

    hours_by_average_duration = sorted(
        [
            {_HOUR_LABEL: k, _AVERAGE_CALL_DURATION_LABEL: v[_AVERAGE_CALL_DURATION_LABEL]}
            for k, v in data_by_hour.items()
            if v[_CALL_COUNT_LABEL] > call_count_cutoff
        ],
        key=lambda x: x[_AVERAGE_CALL_DURATION_LABEL],
    )
    if not hours_by_average_duration:
        return {}

    return {
        "hour_with_shortest_average_call_duration": {
            _HOUR_LABEL: hours_by_average_duration[0][_HOUR_LABEL],
            _AVERAGE_CALL_DURATION_LABEL: hours_by_average_duration[0][_AVERAGE_CALL_DURATION_LABEL],
        },
        "hour_with_longest_average_call_duration": {
            _HOUR_LABEL: hours_by_average_duration[-1][_HOUR_LABEL],
            _AVERAGE_CALL_DURATION_LABEL: hours_by_average_duration[-1][_AVERAGE_CALL_DURATION_LABEL],
        },
    }
