import logging
from typing import Dict, Optional, Tuple

from rest_framework.request import Request

from calls.field_choices import CallDirectionTypes
from core.models import Agent, InsuranceProvider, Practice, PracticeGroup
from core.validation import validate_date_format, validate_dates

# Get an instance of a logger
log = logging.getLogger(__name__)

# TODO: remove, see note in calls/analytics/opportunities/views.py#CallMetricsView
ALL_FILTER_NAME = "all"


def get_validated_call_dates(query_data: Dict) -> Dict:
    """Check if the input dates are of the format YYYY-MM-DD"""
    call_start_time_after = None
    call_start_time_before = None
    errors = {}
    if "call_start_time_after" in query_data.keys():
        call_start_time_after = query_data["call_start_time_after"]

    if "call_start_time_before" in query_data.keys():
        call_start_time_before = query_data["call_start_time_before"]

    try:
        validate_date_format(call_start_time_after)
    except Exception as e:
        errors["call_start_time_after"] = str(e)

    try:
        validate_date_format(call_start_time_before)
    except Exception as e:
        errors["call_start_time_before"] = str(e)

    # Validate the input dates
    dates = validate_dates(call_start_time_after, call_start_time_before)

    if len(dates) != 2:
        external_msg = f"Server error: Please contact r-and-d@peerlogic.com for assistance."
        errors["call_start_time_filters"] = external_msg
        internal_msg = f"Programmer error: Could not find one or more valid date filters configured or otherwise. dates='{dates}'"
        log.error(internal_msg)

    return {"dates": dates, "errors": errors}


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


def get_validated_call_direction(request: Request) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    # TODO: Remove ALL_FILTER_NAME; all is a stop-gap; since its parent was originally using only outbound calls
    # see note in calls/analytics/opportunities/views.py#CallMetricsView
    param_name = "call_direction"
    call_direction = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{call_direction}'"}

    if call_direction not in CallDirectionTypes.choices or call_direction != ALL_FILTER_NAME:
        return None, invalid_error

    return call_direction, None


def get_validated_call_purpose(request: Request) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    param_name = "call_direction"
    call_direction = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{call_direction}'"}

    if call_direction not in CallDirectionTypes.choices or call_direction != ALL_FILTER_NAME:
        return None, invalid_error

    return call_direction, None


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


def get_validated_insurance_provider(request: Request) -> Optional[InsuranceProvider]:
    param_name = "insurance_provider_name"
    insurance_provider_name = request.query_params.get(param_name)

    if not insurance_provider_name:
        return None

    try:
        return InsuranceProvider.objects.get(name=insurance_provider_name)
    except InsuranceProvider.DoesNotExist:
        log.info("Found no insurance provider with name: %s", insurance_provider_name)
        return None
