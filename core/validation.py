from datetime import datetime, timedelta
import json
import logging
import time

from django.conf import settings

# Get an instance of a logger
log = logging.getLogger(__name__)


def validate_date_format(date=None):
    """Validate if the date format is YYYY-mm-dd"""
    try:
        if date != None:
            time.strptime(date, "%Y-%m-%d")
    except Exception as e:
        errorDateFormatMessage = json.dumps({"Message": "Invalid date format. " + str(e)})
        log.error(errorDateFormatMessage)
        raise Exception(errorDateFormatMessage)


def validate_dates(from_date=None, to_date=None):
    """Validates the from_date and to_date for the following conditions

    1. When only one of the dates are given, the search is limited to the default date range
    2. Ensures the to_date is greater than from_date
    """
    today = datetime.today()

    date_range_default_in_days = timedelta(settings.DATE_RANGE_DEFAULT_IN_DAYS)
    date_time_format = "%Y-%m-%d"

    if not from_date and not to_date:
        to_date = today
        from_date = to_date - date_range_default_in_days
    elif not from_date and to_date:
        to_date = datetime.strptime(to_date, date_time_format)
        from_date = to_date - date_range_default_in_days
    elif from_date and not to_date:
        from_date = datetime.strptime(from_date, date_time_format)
        to_date = from_date + date_range_default_in_days
    else:
        to_date = datetime.strptime(to_date, date_time_format)
        from_date = datetime.strptime(from_date, date_time_format)

    # lets make sure that from_date is less than to_date
    if from_date > to_date:
        log.error(f"from_date: '{from_date}' is greater than to_date: '{to_date}'. Swapping dates.")
        temp_to_date = from_date
        from_date = to_date
        to_date = temp_to_date

    # make to_date inclusive, yes this does make the date range default a little wonky
    to_date = to_date + timedelta(days=1)

    return from_date.strftime(date_time_format), to_date.strftime(date_time_format)
