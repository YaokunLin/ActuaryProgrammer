import datetime
from logging import LoggerAdapter
from typing import Any, Dict, Optional, Tuple

import phonenumbers


def parse_nh_datetime_str(nh_datetime_str: Optional[str]) -> Optional[datetime.datetime]:
    if nh_datetime_str is None:
        return

    nh_datetime_str = nh_datetime_str.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(nh_datetime_str)


def get_best_phone_number_from_bio(bio_data: Optional[Dict]) -> Optional[str]:
    if not bio_data:
        return

    # HEREBEDRAGONS: Order matters here!
    possible_phone_keys = (
        "phone_number",
        "cell_phone_number",
        "home_phone_number",
        "work_phone_number",
    )
    for k in possible_phone_keys:
        value = bio_data.get(k)
        if not k:
            continue

        try:
            phonenumbers.parse(value, _check_region=False)
            return value
        except phonenumbers.NumberParseException:  # noqa
            continue


class NexHealthLogAdapter(LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, None)

    def process(self, msg: str, kwargs: Any) -> Tuple[str, Any]:
        return f"[NexHealth] {msg}", kwargs
