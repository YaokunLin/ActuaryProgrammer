import logging
from typing import Dict, Optional

from core.validation import validate_date_format, validate_dates


# Get an instance of a logger
log = logging.getLogger(__name__)


def call_date_validation(query_data: Dict) -> Dict:
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
        internal_msg = f"Programmer error: Could not find one or more valid date filters configured or otherwise. dates='{dates}'"
        external_msg = f"Server error: Please contact r-and-d@peerlogic.com for assistance."
        errors["call_start_time_filters"] = external_msg
        log.error(internal_msg)

    return {"dates": dates, "errors": errors}
