import datetime
from logging import LoggerAdapter
from typing import Any, Dict, Optional, Tuple

import phonenumbers


def parse_nh_datetime_str(nh_datetime_str: Optional[str]) -> Optional[datetime.datetime]:
    if nh_datetime_str is None:
        return

    nh_datetime_str = nh_datetime_str.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(nh_datetime_str)


def get_phone_numbers_from_bio(bio_data: Optional[Dict]) -> Dict[str, Optional[str]]:
    phone_number_best = "phone_number_best"
    phone_number = "phone_number"
    phone_number_mobile = "phone_number_mobile"
    phone_number_home = "phone_number_home"
    phone_number_work = "phone_number_work"
    phone_numbers = {
        phone_number_best: None,
        phone_number: None,
        phone_number_mobile: None,
        phone_number_home: None,
        phone_number_work: None,
    }
    if not bio_data:
        return phone_numbers

    phone_key_mapping = {
        phone_number: "phone_number",
        phone_number_mobile: "cell_phone_number",
        phone_number_home: "home_phone_number",
        phone_number_work: "work_phone_number",
    }
    for k, nh_key in phone_key_mapping.items():
        value = bio_data.get(nh_key)
        if not value:
            continue

        try:
            phonenumbers.parse(value, _check_region=False)
            phone_numbers[k] = value
        except phonenumbers.NumberParseException:  # noqa
            continue

    # Note: This is an important priority order! Order matters
    for k in (phone_number, phone_number_mobile, phone_number_home, phone_number_work):
        if phone_numbers[k]:
            phone_numbers[phone_number_best] = phone_numbers[k]
            break

    return phone_numbers


class NexHealthLogAdapter(LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, None)

    def process(self, msg: str, kwargs: Any) -> Tuple[str, Any]:
        return f"[NexHealth] {msg}", kwargs
