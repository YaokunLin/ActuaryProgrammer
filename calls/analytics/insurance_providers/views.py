import logging
from collections import Counter
from contextlib import suppress
from datetime import timedelta
from typing import Dict, Optional

from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from numpy import percentile
from rest_framework import status, views
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_breakdown_per_practice,
    calculate_call_counts,
    calculate_call_counts_by_date_and_hour,
    calculate_call_counts_per_field,
    calculate_call_counts_per_field_by_date_and_hour,
    calculate_call_counts_per_user,
    calculate_call_counts_per_user_by_date_and_hour,
    calculate_call_non_agent_engagement_type_counts,
    convert_count_results,
    get_call_counts_and_durations_by_weekday_and_hour,
)
from calls.analytics.intents.field_choices import CallOutcomeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.field_choices import CallDirectionTypes
from calls.models import Call
from calls.validation import (
    get_validated_call_dates,
    get_validated_insurance_provider,
    get_validated_practice_group_id,
    get_validated_practice_id,
)
from core.models import InsuranceProviderPhoneNumber

# Get an instance of a logger
log = logging.getLogger(__name__)


class InsuranceProviderInteractionsView(views.APIView):

    # HEREBEDRAGONS: The following variables greatly affect the data that is returned
    #   These values were chosen after a fair bit of trial & error against production data.
    CALL_DURATION_MINIMUM_SECONDS = 140
    CALL_PER_HOUR_PERCENTILE = 60
    LOOKBACK_DAYS = 365

    def get(self, request, format=None):
        insurance_provider = get_validated_insurance_provider(request)
        try:
            verbose = request.query_params.get("verbose", "False").lower() in {"true", "1", "t", "alex"}
        except Exception:
            verbose = False

        if insurance_provider is None:
            return Response({"insurance_provider_name": "Invalid insurance_provider_name"}, status=status.HTTP_400_BAD_REQUEST)

        all_filters = (
            Q(call_direction=CallDirectionTypes.OUTBOUND)
            & Q(call_start_time__gte=timezone.now() - timedelta(days=self.LOOKBACK_DAYS))
            & Q(sip_callee_number__in=insurance_provider.insuranceproviderphonenumber_set.only("phone_number"))
            & Q(duration_seconds__gte=timedelta(seconds=self.CALL_DURATION_MINIMUM_SECONDS))
        )
        calls_qs = Call.objects.filter(all_filters).all()

        response_data = self._get_best_day_and_hour_to_call(calls_qs, verbose=verbose)
        if not response_data:
            return Response(
                {"error": f"Insufficient data to calculate best call day and time for {insurance_provider.name}"}, status=status.HTTP_204_NO_CONTENT
            )

        return Response(response_data)

    @staticmethod
    def _get_best_day_and_hour_to_call(calls_qs: QuerySet, verbose: bool) -> Optional[Dict]:
        if not calls_qs:
            return None

        data_by_weekday_and_hour = get_call_counts_and_durations_by_weekday_and_hour(calls_qs)

        # Constants
        call_count_label = "call_count"
        call_duration_label = "total_call_duration_seconds"
        per_hour_label = "per_hour"
        efficiency_label = "efficiency"
        hour_label = "hour"
        most_efficient_hour_label = "most_efficient_hour"
        highest_efficiency_label = "highest_efficiency"
        day_of_week_label = "day_of_week"

        # Calculate a cutoff for call count per hour. We don't want to suggest an hour with too low volume, only hours with more calls than this
        call_counts_all_hours = []
        for data_for_day_of_week in data_by_weekday_and_hour.values():
            call_counts_all_hours.extend([d[call_count_label] for d in data_for_day_of_week[per_hour_label].values()])
        call_count_cutoff = percentile(call_counts_all_hours, InsuranceProviderInteractionsView.CALL_PER_HOUR_PERCENTILE)

        # Begin calculating best day and time to call
        for day_of_week, data_for_day_of_week in data_by_weekday_and_hour.items():
            # For each day, get the hour with the greatest efficiency which also has >= call_count_cutoff calls made in that hour
            # Store the data about that hour on the day
            d = [
                {efficiency_label: v[efficiency_label], hour_label: k}
                for k, v in data_for_day_of_week[per_hour_label].items()
                if v[call_count_label] >= call_count_cutoff
            ]
            data_per_hour_by_efficiency = sorted(d, key=lambda x: x[efficiency_label])
            if data_per_hour_by_efficiency:
                data_for_day_of_week[most_efficient_hour_label] = data_per_hour_by_efficiency[-1][hour_label]
                data_for_day_of_week[highest_efficiency_label] = data_per_hour_by_efficiency[-1][efficiency_label]

        # Now, sort the days by the one with the highest per-hour efficiency
        days_by_efficient_hours = sorted([d for d in data_by_weekday_and_hour.values()], key=lambda x: x.get(highest_efficiency_label, 0))
        most_efficient_day = days_by_efficient_hours[-1]

        # If we have a day/hour with highest efficiency which also has a non-zero efficiency, we have a winner!
        if most_efficient_day and most_efficient_day.get(highest_efficiency_label):
            # Return the day, hour and average duration for that time period
            most_efficient_day_of_the_week = most_efficient_day[day_of_week_label]
            most_efficient_hour = most_efficient_day[most_efficient_hour_label]
            most_efficient_hour_data = data_by_weekday_and_hour[most_efficient_day_of_the_week][per_hour_label][most_efficient_hour]
            average_duration_at_most_efficient_day_hour = most_efficient_hour_data[call_duration_label] / most_efficient_hour_data[call_count_label]
            return_data = {
                day_of_week_label: most_efficient_day_of_the_week,
                hour_label: most_efficient_hour,
                "call_duration_average_seconds": average_duration_at_most_efficient_day_hour,
            }
            if verbose:
                return_data.update(
                    {
                        "__all_data": data_by_weekday_and_hour,
                        "__call_count_per_hour_minimum": call_count_cutoff,
                        "__call_count_per_hour_percentile": InsuranceProviderInteractionsView.CALL_PER_HOUR_PERCENTILE,
                        "__call_duration_seconds_minimum": InsuranceProviderInteractionsView.CALL_DURATION_MINIMUM_SECONDS,
                        "__calls_this_day_and_hour": most_efficient_hour_data,
                        "__outbound_calls_analyzed": sum(call_counts_all_hours),
                    }
                )
            return return_data

        # No good answers based on data, do not suggest
        return None


class InsuranceProviderMentionedView(views.APIView):
    def get(self, request, format=None):
        size = 10
        with suppress(Exception):
            size = max(0, min(50, int(request.query_params.get("size", size))))

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

        all_filters = (
            Q(
                engaged_in_calls__non_agent_engagement_persona_type__in=[
                    NonAgentEngagementPersonaTypes.NEW_PATIENT,
                    NonAgentEngagementPersonaTypes.EXISTING_PATIENT,
                ]
            )
            & Q(**dates_filter)
            & Q(**practice_filter)
            & Q(**practice_group_filter)
            & Q(mentioned_insurances__keyword__isnull=False)
        )
        calls_qs = Call.objects.select_related("mentioned_insurances").filter(all_filters)

        # Limit to top "size"
        top_mentions = calls_qs.values("mentioned_insurances__keyword").annotate(call_total=Count("id")).order_by("-call_total")[:size]
        results = {"top_insurances_mentioned": [{"insurance": i["mentioned_insurances__keyword"], "count": i["call_total"]} for i in top_mentions]}
        self._normalize_result_insurance_names(results)
        return Response({"results": results})

    @staticmethod
    def _normalize_result_insurance_names(results: Dict) -> None:
        """
        Modifies results in-place to strip excess whitespace and fix capitalization
        """
        for r in results["top_insurances_mentioned"]:
            name = r["insurance"].strip()
            if name and name[0].islower():
                name = name.title()
            r["insurance"] = name


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

        data_by_weekday_and_hour = get_call_counts_and_durations_by_weekday_and_hour(calls_qs)

        analytics = {
            "most_popular_weekday_and_hour": self._get_most_popular_weekday_and_hour(data_by_weekday_and_hour),
            "calls_overall": calculate_call_counts(calls_qs),
            # TODO: PTECH-1240
            # "calls_per_user": calculate_call_counts_per_user(calls_qs),
            # "calls_per_user_by_date_and_hour": calculate_call_counts_per_user_by_date_and_hour(calls_qs),
            # "non_agent_engagement_types": calculate_call_non_agent_engagement_type_counts(calls_qs),
        }
        # TODO: PTECH-1240
        # analytics["calls_by_date_and_hour"] = calculate_call_counts_by_date_and_hour(calls_qs)
        analytics["calls_by_day_of_week"] = self._convert_to_call_counts_per_hour(data_by_weekday_and_hour)

        # TODO: PTECH-1240
        # if calls_qs:
        #     analytics.update(**self.calculate_call_breakdown_per_insurance_provider(calls_qs))
        #
        #     if practice_group_filter:
        #         analytics["calls_per_practice"] = calculate_call_breakdown_per_practice(
        #             calls_qs, practice_group_filter.get("practice__practice_group_id"), analytics["calls_overall"]
        #         )

        return Response({"results": analytics})

    def calculate_call_breakdown_per_insurance_provider(self, calls_qs: QuerySet) -> Dict:
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
            data_per_insurance_provider_name[section_name] = self._aggregate_per_insurance_provider_name(
                data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, section_name, "sum"
            )

        data_per_insurance_provider_name["call_on_hold_seconds_average"] = self._aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_on_hold_seconds_average", "avg"
        )
        data_per_insurance_provider_name["call_seconds_average"] = self._aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_seconds_average", "avg"
        )

        # Success Rate ---
        data_per_insurance_provider_name["call_success_rate"] = dict()
        for k, v in data_per_insurance_provider_name["call_total"].items():
            success_count = data_per_insurance_provider_name["call_success_total"].get(k, None)
            data_per_insurance_provider_name["call_success_rate"][k] = success_count / v if success_count else 0

        return {
            "calls_per_insurance_provider": data_per_insurance_provider_name,
            "calls_per_insurance_provider_by_date_and_hour": self.calculate_call_breakdown_per_insurance_provider_by_date_and_hour(
                calls_qs, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number
            ),
        }

    def calculate_call_breakdown_per_insurance_provider_by_date_and_hour(
        self, calls_qs: QuerySet, num_phone_numbers_per_insurance_provider: Dict, insurance_provider_per_phone_number: Dict
    ) -> Dict:
        data_per_phone_number = calculate_call_counts_per_field_by_date_and_hour(calls_qs, "sip_callee_number")
        data_per_insurance_provider_name = {}

        for section_name in ("call_total", "call_connected_total", "call_seconds_total"):
            data_per_insurance_provider_name[section_name] = self._aggregate_per_insurance_provider_name(
                data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, section_name, "sum", True
            )

        data_per_insurance_provider_name["call_seconds_average"] = self._aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_seconds_average", "avg", True
        )

        data_per_insurance_provider_name["call_on_hold_seconds_average"] = self._aggregate_per_insurance_provider_name(
            data_per_phone_number, num_phone_numbers_per_insurance_provider, insurance_provider_per_phone_number, "call_on_hold_seconds_average", "avg", True
        )
        return data_per_insurance_provider_name

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
                                subvalue[subvalue_key] = subvalue_value / num_phone_numbers
                            new_value[subkey] = subvalue
                        else:
                            new_value[subkey] = subvalue / num_phone_numbers
                else:
                    new_value = v / num_phone_numbers
                data_per_provider[insurance_provider] = new_value

        if is_time_series_breakdown:
            for p, value_per_provider in data_per_provider.items():
                data_per_provider[p] = [{"call_date_hour": k, **v} for k, v in value_per_provider.items()]

        return {p.name: v for p, v in data_per_provider.items()}

    @staticmethod
    def _convert_to_call_counts_per_hour(data_by_weekday_and_hour: Dict) -> Dict:
        return {k: sum(v2["call_count"] for v2 in v["per_hour"].values()) for k, v in data_by_weekday_and_hour.items()}

    @staticmethod
    def _get_most_popular_weekday_and_hour(data_by_weekday_and_hour: Dict) -> Dict:
        top_day = None
        top_hour = None
        top_day_hour_call_count = 0
        top_day_hour_call_count_average_duration_seconds = None
        for day, data_by_weekday in data_by_weekday_and_hour.items():
            for hour, data_by_hour in data_by_weekday["per_hour"].items():
                if data_by_hour["call_count"] > top_day_hour_call_count:
                    top_hour = hour
                    top_day = day
                    top_day_hour_call_count = data_by_hour["call_count"]
                    top_day_hour_call_count_average_duration_seconds = data_by_hour["average_call_duration_seconds"]
        return {
            "weekday": top_day,
            "hour": top_hour,
            "call_count": top_day_hour_call_count,
            "average_call_duration_seconds": top_day_hour_call_count_average_duration_seconds,
        }
