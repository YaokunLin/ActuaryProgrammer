import logging
from copy import deepcopy
from functools import partial
from typing import Any, Dict, List, Optional

from django.db.models import Count, Exists, OuterRef, Q, QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status, views
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_count_opportunities,
    calculate_call_counts,
    calculate_call_counts_and_opportunities_per_user,
    calculate_zero_filled_call_counts_by_day,
    convert_call_counts_to_by_week,
    divide_safely_if_possible,
    map_nested_objs,
    round_if_float,
    safe_divide,
)
from calls.analytics.constants import (
    AVG_VALUE_PER_APPOINTMENT_USD,
    REVENUE_PER_WINBACK_USD,
)
from calls.analytics.query_filters import (
    FAILURE_FILTER,
    INBOUND_FILTER,
    INBOUND_WINBACK_OPPORTUNITY_FILTER,
    NEW_PATIENT_OPPORTUNITIES_FILTER,
    OPPORTUNITIES_FILTER,
    OUTBOUND_FILTER,
    SUCCESS_FILTER,
    get_organization_filter_and_practice_count_for_practice,
)
from calls.models import Call
from calls.validation import (
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


class CallCountsView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        #
        # collect parameters
        #
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        valid_call_direction, call_direction_errors = get_validated_call_direction(request=request)

        valid_practice_id, practice_errors = get_validated_practice_id(request=request)

        #
        # validate parameters
        #
        errors = {}
        if dates_errors:
            errors.update(dates_errors)

        if call_direction_errors:
            errors.update(call_direction_errors)

        if practice_errors:
            errors.update(practice_errors)
        if not practice_errors and not valid_practice_id:
            errors.update({"practice__id": "practice__id must be provided"})

        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        #
        # create individual filters from parameters
        #
        dates = dates_info.get("dates")
        start_date_str = dates[0]
        end_date_str = dates[1]
        dates_filter = Q(call_start_time__gte=start_date_str, call_start_time__lte=end_date_str)

        call_direction_filter = Q()
        if valid_call_direction:
            call_direction_filter = Q(call_direction=valid_call_direction)

        practice = Practice.objects.get(id=valid_practice_id)
        practice_filter = Q(practice__id=valid_practice_id)

        #
        # filter and compute
        #
        base_filters = dates_filter & call_direction_filter
        practice_analytics = self.get_call_counts(base_filters & practice_filter, start_date_str, end_date_str)
        results = practice_analytics

        # calculate organization averages
        organization_filter, num_practices = get_organization_filter_and_practice_count_for_practice(practice=practice)
        if num_practices:
            results["organization_averages"] = self.get_call_counts(base_filters & organization_filter, start_date_str, end_date_str)
            results["organization_averages"] = map_nested_objs(obj=results["organization_averages"], func=partial(divide_safely_if_possible, num_practices))
        else:
            results["organization_averages"] = deepcopy(results)

        return Response({"results": results})

    @staticmethod
    def get_call_counts(filters: Q, start_date_str: str, end_date_str: str) -> Dict[str, Any]:

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


class OpportunitiesView(views.APIView):
    @cache_control(max_age=CACHE_TIME_ANALYTICS_CACHE_CONTROL_MAX_AGE_SECONDS)
    @method_decorator(cache_page(CACHE_TIME_ANALYTICS_SECONDS))
    @method_decorator(vary_on_headers(*ANALYTICS_CACHE_VARY_ON_HEADERS))
    def get(self, request, format=None):
        dates_info = get_validated_call_dates(query_data=request.query_params)
        dates_errors = dates_info.get("errors")

        valid_practice_id, practice_errors = get_validated_practice_id(request=request)

        errors = {}
        if practice_errors:
            errors.update(practice_errors)
        if not practice_errors and not valid_practice_id:
            errors.update({"practice__id": "practice__id must be provided"})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice = Practice.objects.get(id=valid_practice_id)
        practice_filter = Q(practice__id=valid_practice_id)

        dates = dates_info.get("dates")
        dates_filter = Q(call_start_time__gte=dates[0], call_start_time__lte=dates[1])

        opportunities_qs = Call.objects.filter(practice_filter & dates_filter & INBOUND_FILTER & OPPORTUNITIES_FILTER)
        results = self._calculate_opportunities_analytics(opportunities_qs)

        organization_filter, num_practices = get_organization_filter_and_practice_count_for_practice(practice=practice)
        if num_practices:
            org_opportunities_qs = Call.objects.filter(
                Q(practice__organization_id=practice.organization_id) & dates_filter & INBOUND_FILTER & OPPORTUNITIES_FILTER
            )
            results["organization_averages"] = self._calculate_opportunities_analytics(org_opportunities_qs, num_practices)
        else:
            results["organization_averages"] = deepcopy(results)

        return Response(results)

    @staticmethod
    def _calculate_opportunities_analytics(opportunities_qs: QuerySet, num_practices_for_average: Optional[int] = None) -> Dict:
        opportunities_by_outcome = opportunities_qs.values("call_purposes__outcome_results__call_outcome_type").annotate(count=Count("id"))
        d = {r["call_purposes__outcome_results__call_outcome_type"]: r["count"] for r in opportunities_by_outcome}

        total_count = opportunities_qs.count()
        won_count = d.get("success", 0)
        lost_count = d.get("failure", 0)
        open_count = total_count - (won_count + lost_count)
        if num_practices_for_average:
            total_count = safe_divide(total_count, num_practices_for_average)
            won_count = safe_divide(won_count, num_practices_for_average)
            lost_count = safe_divide(lost_count, num_practices_for_average)
            open_count = safe_divide(open_count, num_practices_for_average)
        opportunity_counts = {
            "total": total_count,
            "won": won_count,
            "lost": lost_count,
            "open": open_count,
        }
        opportunity_values = {
            "total": round_if_float(total_count * AVG_VALUE_PER_APPOINTMENT_USD),
            "won": round_if_float(won_count * AVG_VALUE_PER_APPOINTMENT_USD),
            "lost": round_if_float(lost_count * AVG_VALUE_PER_APPOINTMENT_USD),
            "open": round_if_float(open_count * AVG_VALUE_PER_APPOINTMENT_USD),
        }
        return {
            "counts": opportunity_counts,
            "values": opportunity_values,
        }


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
            error_message = "practice__id or organization__id must be provided, but not both."
            errors.update({"practice__id": error_message, "organization__id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = Q()
        if valid_practice_id:
            practice_filter = Q(practice_id=valid_practice_id)

        # date filters
        dates = dates_info.get("dates")
        start_date_str = dates[0]
        end_date_str = dates[1]
        dates_filter = Q(call_start_time__gte=start_date_str, call_start_time__lte=end_date_str)

        filters = dates_filter & practice_filter & INBOUND_FILTER

        aggregates = {
            "agent": calculate_call_counts_and_opportunities_per_user(filters),  # call counts per caller (agent) phone number
        }

        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: start_date_str,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: end_date_str,
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
            error_message = "practice__id or organization__id must be provided, but not both."
            errors.update({"practice__id": error_message, "organization__id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        # practice filter
        practice_filter = Q()
        if valid_practice_id:
            practice_filter = Q(practice_id=valid_practice_id)

        organization_filter = Q()
        if valid_organization_id:
            organization_filter = Q(practice__organization_id=valid_organization_id)

        # date filters
        dates = dates_info.get("dates")
        call_start_time__gte = dates[0]
        call_start_time__lte = dates[1]
        dates_filter = Q(call_start_time__gte=call_start_time__gte, call_start_time__lte=call_start_time__lte)

        base_filters = dates_filter & practice_filter & organization_filter & NEW_PATIENT_OPPORTUNITIES_FILTER & INBOUND_FILTER

        # aggregate analytics
        aggregates = {}
        new_patient_opportunities_qs = Call.objects.filter(base_filters)
        aggregates["new_patient_opportunities_total"] = new_patient_opportunities_qs.count()
        aggregates["new_patient_opportunities_time_series"] = self._calculate_new_patient_opportunities_time_series(
            new_patient_opportunities_qs, dates[0], dates[1]
        )

        new_patient_opportunities_won_qs = Call.objects.filter(base_filters & SUCCESS_FILTER)
        aggregates["new_patient_opportunities_won_total"] = new_patient_opportunities_won_qs.count()

        new_patient_opportunities_lost_qs = Call.objects.filter(base_filters & FAILURE_FILTER)
        aggregates["new_patient_opportunities_lost_total"] = new_patient_opportunities_lost_qs.count()

        aggregates["new_patient_opportunities_conversion_rate_total"] = safe_divide(
            aggregates["new_patient_opportunities_won_total"], aggregates["new_patient_opportunities_total"]
        )

        if organization_filter:
            per_practice_averages = {}
            num_practices = Practice.objects.filter(organization_id=valid_organization_id).count()
            per_practice_averages["new_patient_opportunities"] = safe_divide(aggregates["new_patient_opportunities_total"], num_practices)
            per_practice_averages["new_patient_opportunities_won"] = safe_divide(aggregates["new_patient_opportunities_won_total"], num_practices)
            per_practice_averages["new_patient_opportunities_lost"] = safe_divide(aggregates["new_patient_opportunities_lost_total"], num_practices)
            aggregates["new_patient_opportunities_conversion_rate"] = safe_divide(aggregates["new_patient_opportunities_conversion_rate_total"], num_practices)
            aggregates["per_practice_averages"] = per_practice_averages

        # display syntactic sugar
        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: call_start_time__gte,
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: call_start_time__lte,
        }

        return Response({"filters": display_filters, "results": aggregates})

    @staticmethod
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
                rate = safe_divide(record["value"], total_for_date)
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
            error_message = "practice__id or organization__id must be provided, but not both."
            errors.update({"practice__id": error_message, "organization__id": error_message})
        if dates_errors:
            errors.update(dates_errors)
        if errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        practice_filter = Q()
        if valid_practice_id:
            practice_filter = Q(practice__id=valid_practice_id)

        organization_filter = Q()
        if valid_organization_id:
            organization_filter = Q(practice__organization__id=valid_organization_id)

        dates = dates_info.get("dates")
        dates_filter = Q(call_start_time__gte=dates[0], call_start_time__lte=dates[1])

        calls_qs = Call.objects.filter(dates_filter & practice_filter & organization_filter)

        winback_patient_phone_numbers = self._get_winback_opportunity_phone_numbers(calls_qs)
        callee_number_filter = Q(sip_callee_number__in=winback_patient_phone_numbers)

        winback_opportunities_total_qs = self._filter_one_call_per_number(calls_qs.filter(INBOUND_WINBACK_OPPORTUNITY_FILTER))
        winback_opportunities_won_qs = self._filter_one_call_per_number(
            calls_qs.filter(OUTBOUND_FILTER & callee_number_filter & SUCCESS_FILTER),
            calls_qs.filter(OUTBOUND_FILTER & callee_number_filter),
            phone_number_field_name="sip_callee_number",
            earliest_or_latest="latest",
        )
        winback_opportunities_lost_qs = self._filter_one_call_per_number(
            calls_qs.filter(OUTBOUND_FILTER & callee_number_filter & FAILURE_FILTER),
            calls_qs.filter(OUTBOUND_FILTER & callee_number_filter),
            phone_number_field_name="sip_callee_number",
            earliest_or_latest="latest",
        )

        aggregates = {}
        aggregates["winback_opportunities_total"] = winback_patient_phone_numbers.count()
        aggregates["winback_opportunities_won"] = winback_opportunities_won_qs.count()
        aggregates["winback_opportunities_revenue_dollars"] = aggregates["winback_opportunities_won"] * REVENUE_PER_WINBACK_USD
        aggregates["winback_opportunities_lost"] = winback_opportunities_lost_qs.count()

        # Think of this more in terms of getting a breakdown of opportunities attempted vs open instead of
        #     thinking of this as a count of attempts (not distinct to callee_number)
        aggregates["winback_opportunities_attempted"] = aggregates.get("winback_opportunities_won", 0) + aggregates.get("winback_opportunities_lost", 0)
        aggregates["winback_opportunities_open"] = aggregates.get("winback_opportunities_total", 0) - aggregates.get("winback_opportunities_attempted", 0)
        aggregates["winback_opportunities_time_series"] = self._calculate_winback_time_series(
            winback_opportunities_total_qs, winback_opportunities_won_qs, winback_opportunities_lost_qs, dates[0], dates[1]
        )

        display_filters = {
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__gte"]: dates[0],
            self.QUERY_FILTER_TO_HUMAN_READABLE_DISPLAY_NAME["call_start_time__lte"]: dates[1],
        }

        return Response({"filters": display_filters, "results": aggregates})

    @staticmethod
    def _filter_one_call_per_number(
        calls_qs: QuerySet, dedupe_qs: Optional[QuerySet] = None, phone_number_field_name: str = "sip_caller_number", earliest_or_latest: str = "earliest"
    ) -> QuerySet:
        """
        Deduplicate a given queryset on caller or callee number.

        phone_number_field_name is "sip_callee_number" or "sip_caller_number"
        earliest_or_latest is "earliest" or "latest"

        Different querysets may be provided for calls_qs / dedupe_qs query. An example of why this is useful:
          In a given time window, we want to count winbacks lost deduplicated on callee number. To achieve this,
          we need to consider all outcome types for purposes of deduplication. However, we want to make sure we
          only return calls with a success outcome. So the subquery does not filter on outcome, but the resulting
          queryset DOES filter on outcome. This stops us from calling an opportunity lost, when it might actually
          be won later on in the same time window.
        """
        if dedupe_qs is None:
            dedupe_qs = calls_qs

        same_phone_number_later_time_qs = dedupe_qs.filter(
            **{
                phone_number_field_name: OuterRef(phone_number_field_name),
                f"call_start_time__{'lt' if earliest_or_latest == 'earliest' else 'gt'}": OuterRef("call_start_time"),
            }
        )
        return calls_qs.filter(~Q(Exists(same_phone_number_later_time_qs)))

    @staticmethod
    def _get_winback_opportunity_phone_numbers(calls_qs: QuerySet):
        return calls_qs.filter(INBOUND_WINBACK_OPPORTUNITY_FILTER).values_list("sip_caller_number", flat=True).distinct()

    @staticmethod
    def _calculate_winback_time_series(
        winbacks_total_qs: QuerySet, winbacks_won_qs: QuerySet, winbacks_lost_qs: QuerySet, start_date: str, end_date: str
    ) -> Dict:
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
