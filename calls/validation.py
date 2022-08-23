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
        msg = f"We must have 2 dates to filter calls by. This should not happen! dates='{dates}'"
        errors["call_start_time_filters"] = msg
        log.error(msg)

    return {"dates": dates, "errors": errors}
