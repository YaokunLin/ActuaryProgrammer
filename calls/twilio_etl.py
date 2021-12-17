import logging

from django.conf import settings
from twilio.rest import Client
from twilio.rest.lookups.v1.phone_number import PhoneNumberInstance

from .field_choices import (
    TelecomCallerNameInfoTypes,
    TelecomCallerNameInfoSourceTypes,
    TelecomCarrierTypes,
)
from .models import TelecomCallerNameInfo


# Get an instance of a logger
log = logging.getLogger(__name__)


def get_caller_name_info_from_twilio(phone_number: str, client: Client=None) -> PhoneNumberInstance:
    """Retrieves caller information from the Twilio API."""
    # Phone Number Formats:
    # - E.164 International Standard (https://en.wikipedia.org/wiki/E.164) - Use this one
    # - National Formatting (012) 345-6789

    # Authorization: Basic <credentials> - handled by Twilio client
    # username = key_sid
    # password = key_secret

    # Example from API docs
    #   curl -X GET 'https://lookups.twilio.com/v1/PhoneNumbers/3105555555' \
    #   -u ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX:your_auth_token

    # twilio lookup API: https://support.twilio.com/hc/en-us/articles/360050891214-Getting-Started-with-the-Twilio-Lookup-API
    # Example lookups in python: https://www.twilio.com/docs/lookup/api
    # API Explorer - "Lookup": https://console.twilio.com/us1/develop/api-explorer/endpoints?frameUrl=%2Fconsole%2Fapi-explorer%3Fx-target-region%3Dus1&currentFrameUrl=%2Fconsole%2Fapi-explorer%2Flookup%2Flookup-phone-numbers%2Ffetch%3F__override_layout__%3Dembed%26bifrost%3Dtrue%26x-target-region%3Dus1

    if not client:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # lookup value in twilio
    # you must specify the types whose values you want to have filled in, otherwise they will be None
    phone_number_info = client.lookups.v1.phone_numbers(phone_number).fetch(type=["caller-name", "carrier"])
    return phone_number_info


def validate_twilio_data(twilio_phone_number_info: PhoneNumberInstance):
    # validate caller_name
    caller_name_section = twilio_phone_number_info.caller_name
    if caller_name_section is None:
        raise ValueError("Twilio response missing caller_name section!")

    error_code = caller_name_section.get("error_code")
    if error_code is not None:
        raise ValueError(f"Twilio response has an error_code of '{error_code}' in caller_name section!")

    # validate carrier_type
    carrier_type_section = twilio_phone_number_info.caller_name
    if carrier_type_section is None:
        raise ValueError("Twilio response missing carrier_type section!")
    
    if error_code is not None:
        raise ValueError(f"Twilio response has an error_code of '{error_code}' in carrier_type section!")


def update_telecom_caller_name_info_with_twilio_data(telecom_caller_name_info: TelecomCallerNameInfo, twilio_phone_number_info: PhoneNumberInstance) -> None:
    # Shape of the twilio data
    # {
    #    "caller_name": {"caller_name": "", "caller_type", "error_code": ""}
    #    "carrier": {"mobile_country_code": "313", "mobile_network_code": "981", "name": "Bandwidth/13 - Bandwidth.com - SVR", "type": "voip", "error_code": None}
    #    "country_code": "",
    #    "phone_number": "",
    #    "national_format": ""
    # }
    log.debug(f"Twilio phone number object with all properties: '{twilio_phone_number_info.__dict__}'")

    log.info(
        "Attempting to get data from twilio's response to update telecom caller name info. NOTE: validation has occurred before this point. If there is an error in this function, we need to update our validation codes!"
    )

    source = TelecomCallerNameInfoSourceTypes.TWILIO

    # raw - extract and load
    telecom_caller_name_info.extract_raw_json = twilio_phone_number_info._properties

    # root - extraction
    phone_number = twilio_phone_number_info.phone_number
    country_code = twilio_phone_number_info.country_code

    # root - load
    telecom_caller_name_info.phone_number = phone_number
    telecom_caller_name_info.country_code = country_code

    # caller_name section - extraction
    caller_name_section = twilio_phone_number_info.caller_name
    caller_name = caller_name_section.get("caller_name", "")
    caller_name = caller_name or ""

    caller_type = caller_name_section.get("caller_type", "")  # BUSINESS CONSUMER UNDETERMINED
    caller_type = caller_type.lower()  # accept empty strings but not null
    if caller_type not in TelecomCallerNameInfoTypes.values:
        caller_type = ""

    # caller_name section - load
    telecom_caller_name_info.caller_name = caller_name
    telecom_caller_name_info.caller_name_type = caller_type
    telecom_caller_name_info.source = source

    # carrier type - extraction
    carrier_section = twilio_phone_number_info.carrier
    mobile_country_code = carrier_section.get("mobile_country_code", "")
    mobile_network_code = carrier_section.get("mobile_network_code", "")
    carrier_name = carrier_section.get("name", "")
    carrier_type = carrier_section.get("type", "")
    carrier_type = carrier_type.lower()  # accept empty strings but not null
    if carrier_type not in TelecomCarrierTypes.values:
        carrier_type = ""

    # carrier type - load
    telecom_caller_name_info.mobile_country_code = mobile_country_code
    telecom_caller_name_info.mobile_network_code = mobile_network_code
    telecom_caller_name_info.carrier_name = carrier_name
    telecom_caller_name_info.carrier_type = carrier_type

    log.info("Updated local model with twilio response data")
