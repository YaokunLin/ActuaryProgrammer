import datetime
from dataclasses import asdict, dataclass, fields
from logging import LoggerAdapter, getLogger
from typing import Any, Dict, Optional, Tuple

import phonenumbers
from google.api_core.exceptions import NotFound as GCPNotFoundError
from google.cloud import secretmanager

from peerlogic.settings import PHONENUMBER_DEFAULT_REGION, PROJECT_ID


class NexHealthLogAdapter(LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, None)

    def process(self, msg: str, kwargs: Any) -> Tuple[str, Any]:
        return f"[NexHealth] {msg}", kwargs


log = NexHealthLogAdapter(getLogger(__name__))


def persist_nexhealth_access_token(nexhealth_subdomain: str, nexhealth_access_token: str) -> None:
    secret_parent, secret_id, secret_name, latest_secret_version_name = _get_secret_identifiers_for_nexhealth_subdomain(nexhealth_subdomain)
    secrets_client = secretmanager.SecretManagerServiceClient()
    existing_secret_value = None
    try:
        existing_secret_value = get_nexhealth_access_token_for_subdomain(nexhealth_subdomain, secrets_client)
        log.info(f"Found existing secret for {secret_name}.")
    except GCPNotFoundError:
        log.info(f"No existing secret found. Creating new secret for {secret_name}.")
        secrets_client.create_secret(
            request={
                "parent": secret_parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )

    if existing_secret_value != nexhealth_access_token:
        log.info(f"Adding new secret version for {secret_name}")
        secrets_client.add_secret_version(request={"parent": secret_name, "payload": {"data": nexhealth_access_token.encode()}})
        log.info(f"Added new secret version for {secret_name}")
    else:
        log.info(f"New secret version matches old secret version. Not updating {secret_name}")


def get_nexhealth_access_token_for_subdomain(nexhealth_subdomain: str, secrets_client: Optional[secretmanager.SecretManagerServiceClient] = None) -> str:
    if secrets_client is None:
        secrets_client = secretmanager.SecretManagerServiceClient()
    _, _, _, latest_secret_version_name = _get_secret_identifiers_for_nexhealth_subdomain(nexhealth_subdomain)
    secret_value_response = secrets_client.access_secret_version(name=latest_secret_version_name)
    return secret_value_response.payload.data.decode()


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
                        try:
                            validated_number = phonenumbers.parse(v)
                        except phonenumbers.NumberParseException:  # noqa
                            validated_number = phonenumbers.parse(v, PHONENUMBER_DEFAULT_REGION)
                        number_as_e164 = phonenumbers.format_number(validated_number, phonenumbers.PhoneNumberFormat.E164)
                        setattr(self, f.name, number_as_e164)
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


def _get_secret_identifiers_for_nexhealth_subdomain(nexhealth_subdomain: str) -> Tuple[str, str, str, str]:
    """
    Returns secret_parent, secret_name, latest_secret_version_name
    """
    secret_parent = f"projects/{PROJECT_ID}"
    secret_id = f"NEXHEALTH_CREDENTIAL_{nexhealth_subdomain.upper().replace('-', '_')}"
    secret_name = f"{secret_parent}/secrets/{secret_id}"
    latest_secret_version_name = f"{secret_name}/versions/latest"
    return secret_parent, secret_id, secret_name, latest_secret_version_name
