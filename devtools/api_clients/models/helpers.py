import logging
from datetime import datetime
from typing import Dict, List


def normalize_duration_string_into_seconds(time_string: str) -> int:
    """Given a time string like so: 01:01:09, returns 3669"""

    date_time = datetime.strptime(time_string, "%H:%M:%S")  # 1900-01-01 01:01:09
    a_timedelta = date_time - datetime(1900, 1, 1)
    return a_timedelta.total_seconds()


def normalize_date_times_for_event(event: Dict, key_names_with_dates: List[str], format: str = "%Y-%m-%d %H:%M:%S.%f %z") -> Dict:
    event_normalized = event.copy()
    for key_name in key_names_with_dates:
        datetime_base = event_normalized.get(key_name, None)
        try:
            datetime_normalized = datetime.strptime(datetime_base, format)
            event_normalized[key_name] = datetime_normalized
        except Exception as e:
            logging.warn(e)
            logging.warn(
                f"Recoverable problem occurred when attempting to coerce datetime for key: '{key_name}', value: '{datetime_base}' Setting value to None."
            )
            event_normalized[key_name] = None

    return event_normalized
