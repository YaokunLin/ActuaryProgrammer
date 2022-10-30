import logging
from typing import Dict, Optional, Tuple

import backports.zoneinfo as zoneinfo
from rest_framework.request import Request

from calls.field_choices import CallDirectionTypes
from core.models import Agent, InsuranceProvider, Organization, Practice
from core.validation import validate_date_format, validate_dates

# Get an instance of a logger
log = logging.getLogger(__name__)


def get_validated_call_dates(request: Request) -> Dict:
    """
    TODO Kyle: Meaningful docstring
    """

    header_name = "HTTP_TIMEZONE"
    tzname = request.META.get(header_name)
    if not tzname or tzname not in zoneinfo.available_timezones():
        tzname = "UTC"

    tzinfo = zoneinfo.ZoneInfo(tzname)

    query_data = request.query_params
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

    if errors:
        return {"dates": None, "errors": errors}

    # Validate the input dates
    dates = validate_dates(call_start_time_after, call_start_time_before, tzinfo)

    if len(dates) != 2:
        external_msg = f"Server error: Please contact r-and-d@peerlogic.com for assistance."
        errors["call_start_time_filters"] = external_msg
        internal_msg = f"Programmer error: Could not find one or more valid date filters configured or otherwise. dates='{dates}'"
        log.error(internal_msg)

    return {"dates": dates, "errors": errors}


# TODO: move to core app
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


def get_validated_call_direction(request: Request, default: Optional[str] = None) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    param_name = "call_direction"
    call_direction = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{call_direction}'"}

    if call_direction is None:
        return default, None

    call_direction = call_direction.lower()
    if call_direction not in CallDirectionTypes:
        return None, invalid_error

    return call_direction, None


def get_validated_organization_id(request: Request) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    param_name = "organization__id"
    organization_id = request.query_params.get(param_name)
    invalid_error = {param_name: f"Invalid {param_name}='{organization_id}'"}

    if not organization_id:
        return None, None

    if request.user.is_staff or request.user.is_superuser:
        if Organization.objects.filter(id=organization_id).exists():
            return organization_id, None
        return None, invalid_error

    # Can see any practice's resources if you are an assigned agent to a practice
    allowed_organization_ids = Agent.objects.filter(user=request.user).values_list("practice__organization__id", flat=True)
    if organization_id not in allowed_organization_ids:
        return None, {param_name: f"Invalid {param_name}='{organization_id}'"}

    return organization_id, None


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


def get_validated_query_param_bool(request: Request, param_name: str, default_value: bool = False) -> bool:
    param_value = request.query_params.get(param_name, None)
    if param_value is None:
        return default_value

    if param_value and param_value.lower() in ("true", "1", "t"):
        return True

    return False
