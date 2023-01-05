import datetime
from dataclasses import asdict, dataclass, fields
from logging import LoggerAdapter
from typing import Any, Dict, Optional, Tuple

import phonenumbers


def parse_nh_datetime_str(nh_datetime_str: Optional[str]) -> Optional[datetime.datetime]:
    if nh_datetime_str is None:
        return

    nh_datetime_str = nh_datetime_str.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(nh_datetime_str)


def get_phone_numbers_from_bio(bio_data: Optional[Dict]) -> Dict[str, Optional[str]]:
    @dataclass
    class _PhoneNumbers:
        phone_number: Optional[str] = None
        phone_number_mobile: Optional[str] = None
        phone_number_home: Optional[str] = None
        phone_number_work: Optional[str] = None

        def __init__(
            self,
            phone_number: Optional[str] = None,
            phone_number_mobile: Optional[str] = None,
            phone_number_home: Optional[str] = None,
            phone_number_work: Optional[str] = None,
        ):
            self.phone_number = phone_number
            self.phone_number_mobile = phone_number_mobile
            self.phone_number_home = phone_number_home
            self.phone_number_work = phone_number_work
            for f in fields(self):
                v = getattr(self, f.name, None)
                if v is not None:
                    try:
                        phonenumbers.parse(v, _check_region=False)
                    except phonenumbers.NumberParseException:  # noqa
                        setattr(self, f.name, None)

            if self.phone_number is None:
                # Set phone_number to be the "best" phone number if it is not populated
                self.phone_number = (
                    self.phone_number_mobile if self.phone_number_mobile else self.phone_number_home if self.phone_number_home else self.phone_number_work
                )

    return asdict(
        _PhoneNumbers(
            phone_number=bio_data.get("phone_number"),
            phone_number_mobile=bio_data.get("cell_phone_number"),
            phone_number_home=bio_data.get("home_phone_number"),
            phone_number_work=bio_data.get("work_phone_number"),
        )
    )


class NexHealthLogAdapter(LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, None)

    def process(self, msg: str, kwargs: Any) -> Tuple[str, Any]:
        return f"[NexHealth] {msg}", kwargs
