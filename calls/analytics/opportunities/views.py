import logging
from typing import Dict

from django.db.models import (
    Avg,
    Count,
    Q,
    QuerySet,
    Sum,
)
from rest_framework import status, views
from rest_framework.response import Response

from calls.field_choices import (
    CallDirectionTypes,
)
from calls.analytics.intents.field_choices import CallOutcomeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.models import (
    Call,
)
from calls.validation import validate_call_dates
from core.models import Agent


# Get an instance of a logger
log = logging.getLogger(__name__)


def authorize_and_validate_practice_id(request):
    practice__id = request.query_params.get("practice__id")

    if not practice__id:
        return False, {"practice__id": "Must include practice id for call analytics."}

    if request.user.is_staff or request.user.is_superuser:
        return True, None

    # Can see any practice's resources if you are an assigned agent to a practice
    allowed_practice_ids = Agent.objects.filter(user=request.user.id).values("practice__id")
    if practice__id not in allowed_practice_ids:
        return False, {"practice__id": f"Not allowed to see resources with practice__id='{practice__id}'"}

    return True, None


class CallMetricsView(views.APIView):

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

        # set re-usable filters
        filters = Q(call_direction=CallDirectionTypes.OUTBOUND) & Q(**dates_filter) & Q(**practice_filter)

        # set re-usable filtered queryset
        calls_qs = Call.objects.filter(filters)

        # perform analytics
        count_analytics = get_call_counts_from_qs(calls_qs)

        return Response({"results": count_analytics})


def get_call_counts_from_qs(calls_qs: QuerySet) -> Dict:
    # get call counts
    count_analytics = calls_qs.aggregate(
        call_count=Count("id"),
        call_connected_total=Count("call_connection", filter=Q(call_connection="connected")),
        call_seconds_total=Sum("duration_seconds"),
        call_seconds_average=Avg("duration_seconds"),
    )

    # Get sentiment counts
    call_sentiment_analytics_qs = calls_qs.values(
        "call_sentiments__caller_sentiment_score"
    ).annotate(
        call_sentiment_count=Count("call_sentiments__caller_sentiment_score")
    )
    count_analytics["call_sentiment_counts"] = {
        sentiment_row["call_sentiments__caller_sentiment_score"]: sentiment_row["call_sentiment_count"]
        for sentiment_row in call_sentiment_analytics_qs
    }

    return count_analytics


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
