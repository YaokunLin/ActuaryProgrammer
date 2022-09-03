import logging
from typing import Dict, Optional, Tuple

from django.db.models import Avg, Count, Q, QuerySet, Sum
from rest_framework.request import Request

from core.models import Agent, Practice, PracticeGroup

# Get an instance of a logger
log = logging.getLogger(__name__)


def get_validated_practice_id(request: Request) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    param_name = "practice__id"
    practice_id = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{practice_id}'"}

    if not practice_id:
        return None, None

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
    invalid_error = {param_name: f"Invalid {param_name}='{practice_group_id}'"}

    if not practice_group_id:
        return None, None

    if request.user.is_staff or request.user.is_superuser:
        if PracticeGroup.objects.filter(id=practice_group_id).exists():
            return practice_group_id, None
        return None, invalid_error

    # Can see any practice's resources if you are an assigned agent to a practice
    allowed_practice_group_ids = Agent.objects.filter(user=request.user).values_list("practice__practice_group__id", flat=True)
    if practice_group_id not in allowed_practice_group_ids:
        return None, {param_name: f"Invalid {param_name}='{practice_group_id}'"}

    return practice_group_id, None


def calculate_call_counts(calls_qs: QuerySet) -> Dict:
    # get call counts
    count_analytics = calls_qs.aggregate(
        call_total=Count("id"),
        call_connected_total=Count("call_connection", filter=Q(call_connection="connected")),
        call_seconds_total=Sum("duration_seconds"),
        call_seconds_average=Avg("duration_seconds"),
    )

    return count_analytics
