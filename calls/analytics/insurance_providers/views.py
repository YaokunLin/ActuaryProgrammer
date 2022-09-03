import logging

from django.db.models import Q
from rest_framework import status, views
from rest_framework.response import Response

from calls.analytics.aggregates import (
    calculate_call_breakdown_per_practice,
    calculate_call_counts,
    calculate_call_counts_per_user,
    calculate_call_counts_per_user_time_series,
    calculate_outbound_call_non_agent_engagement_type_counts,
)
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
            "non_agent_engagement_types": calculate_outbound_call_non_agent_engagement_type_counts(calls_qs),
        }
        if practice_group_filter:
            analytics["calls_per_practice"] = calculate_call_breakdown_per_practice(
                calls_qs, practice_group_filter.get("practice__practice_group_id"), analytics["calls_overall"]
            )

        return Response({"results": analytics})
