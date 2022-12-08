import datetime
from typing import Dict, Optional

import phonenumbers


def parse_nh_datetime_str(nh_datetime_str: str) -> datetime.datetime:
    nh_datetime_str = nh_datetime_str.replace("Z", "")
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
