import logging

from django.conf import settings
from django.db import DatabaseError
from django.http import (
    HttpResponseBadRequest,
    Http404,
)
from phonenumber_field.modelfields import to_python as to_phone_number
from twilio.rest.lookups.v1.phone_number import PhoneNumberInstance
from rest_framework import viewsets
from rest_framework.exceptions import bad_request
from rest_framework.response import Response
from twilio.base.exceptions import TwilioException
from twilio.rest import Client


from .field_choices import (
    TelecomCallerNameInfoTypes,
    TelecomCallerNameInfoSourceTypes,
)

from .models import (
    Call,
    CallLabel,
    TelecomCallerNameInfo,
)
from .serializers import (
    CallSerializer,
    CallLabelSerializer,
    TelecomCallerNameInfoSerializer,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class CallViewset(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer


class CallLabelViewset(viewsets.ModelViewSet):
    queryset = CallLabel.objects.all()
    serializer_class = CallLabelSerializer


class TelecomCallerNameInfoViewSet(viewsets.ModelViewSet):
    queryset = TelecomCallerNameInfo.objects.all()
    serializer_class = TelecomCallerNameInfoSerializer
    filter_fields = ["caller_name_type", "source"]
    search_fields = ["caller_name"]
    ordering = ["caller_name"]

    def retrieve(self, request, pk):
        phone_number_raw = pk
        log.info(f"Retrieving caller_name_info for phone_number: '{phone_number_raw}'")

        # validate and normalize phone number
        try:
            log.info(f"Validating phone number: phone_number_raw: '{phone_number_raw}'")
            phone_number = to_phone_number(phone_number_raw)  # this will explode for obviously bad phone numbers
            if not phone_number.is_valid():  # true for not so obviously bad phone numbers
                msg = f"Invalid phone number detected, phone_number_raw: '{phone_number_raw}'"
                log.error(msg)
                raise TypeError(msg)
        except Exception as e:
            return HttpResponseBadRequest(f"Invalid phone number detected, phone_number_raw: '{phone_number_raw}'")

        # be aware strange phone numbers will survive the above
        # strange phone numbers from the above include ones where a phone number has numbers appended: 14401234567bb
        # strange phone numbers like this will be accepted by twilio which will truncate the bad parts
        # we MUST normalize to get something reasonable-looking for our system's storage
        log.info(f"Normalizing phone_number_raw: '{phone_number_raw}'")
        phone_number = phone_number.as_e164
        log.info(f"Normalized phone_number_raw: '{phone_number_raw}' to phone_number: '{phone_number}'")

        # use whatever we find and 404 if we don't find anything
        if not settings.TWILIO_IS_ENABLED:
            log.info(f"Twilio is off. Using existing database lookup for phone_number: '{phone_number}'")
            return super().retrieve(request, phone_number)

        # search database for record
        log.info(f"Performing lookups for phone_number: '{phone_number}'")
        telecom_caller_name_info, created = TelecomCallerNameInfo.objects.get_or_create(phone_number=phone_number)

        # existing row that has legitimate values and is not stale
        if not created and telecom_caller_name_info.caller_name_type is not None and not telecom_caller_name_info.is_caller_name_info_stale():

            log.info(f"Using existing caller_name_info from database since it exists and is not stale / expired for phone_number: '{phone_number}'.")
            return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

        # fetch from twilio and update database
        try:
            # get and validate twilio data
            log.info(f"Twilio is on and we have stale / expired or missing data. Requesting data from twilio for phone_number: '{phone_number}'")
            twilio_caller_name_info = get_caller_name_info_from_twilio(phone_number=phone_number)
            validate_twilio_data(twilio_caller_name_info)

            # update local object
            log.info(f"Saving data from twilio for phone_number: '{phone_number}'")
            update_telecom_caller_name_info_with_twilio_data(telecom_caller_name_info, twilio_caller_name_info)
            telecom_caller_name_info.save()
            log.info(f"Saved data from twilio for phone_number: '{phone_number}'")
        except TwilioException as e:
            log.exception(
                f"Unable to call Twilio to obtain or update caller name information for: '{phone_number}'. This does not mean we were unable to fulfill the request for data if we have a stale value available.",
                e,
            )
        except ValueError as e:
            log.exception(f"Problems occurred extracting values from Twilio's response for: '{phone_number}'", e)
        except DatabaseError as e:
            log.exception(
                f"Problem occurred saving updated values for phone number: '{phone_number}'. This does not mean we were unable to fulfill the request for data if we have a stale value available",
                e,
            )

        # validate that we have a legitimate value from the database
        # we may have a legitimate but stale value, that's fine
        # however, if we don't have a caller_name_type record, this is an incomplete record from our get_or_create above then roll it back / kill it
        log.info(f"Verifying we have a legitimate caller_name_info to send to client for '{phone_number}'")
        if created and telecom_caller_name_info.caller_name_type is None:
            log.warn(
                f"Incompleted caller_name_info record. No stale or fresh caller_name_info data is available. We've created a new caller_name_info object but couldn't fill it with Twilio values. ROLLING BACK. phone_number: '{phone_number}'"
            )
            telecom_caller_name_info.delete()
            log.warn(f"ROLLED BACK / DELETED incomplete record for phone_number: '{phone_number}'")
            raise Http404

        # win
        log.info(f"caller_name_info available to send to client for '{phone_number}'")
        return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)


def get_caller_name_info_from_twilio(phone_number: str, client: Client = None) -> PhoneNumberInstance:
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
    caller_name_section = twilio_phone_number_info.caller_name
    if caller_name_section is None:
        raise ValueError("Twilio response missing caller_name section!")

    error_code = caller_name_section.get("error_code")
    if error_code is not None:
        raise ValueError(f"Twilio response has an error_code of '{error_code}' in caller_name section!")


def update_telecom_caller_name_info_with_twilio_data(telecom_caller_name_info: TelecomCallerNameInfo, twilio_phone_number_info: PhoneNumberInstance) -> None:
    # Shape of the data
    # {
    #    "caller_name": {"caller_name": "", "caller_type", "error_code": ""}
    #    "carrier": {"mobile_country_code": "313", "mobile_network_code": "981", "name": "Bandwidth/13 - Bandwidth.com - SVR", "type": "voip", "error_code": None}
    #    "country_code": "",
    #    "phone_number": "",
    #    "national_format": ""
    # }
    log.debug(twilio_phone_number_info.__dict__)

    log.info(
        "Attempting to get data from twilio's response to update telecom caller name info. NOTE: validation has occurred before this point. If there is an error in this function, we need to update our validation codes!"
    )
    caller_name_section = twilio_phone_number_info.caller_name
    caller_name = caller_name_section.get("caller_name", "")
    caller_name = caller_name or ""
    
    caller_type = caller_name_section.get("caller_type", "")  # BUSINESS CONSUMER UNDETERMINED
    caller_type = caller_type.lower()  # accept empty strings but not null
    if caller_type not in TelecomCallerNameInfoTypes.values:
        caller_type = None
    
    phone_number = twilio_phone_number_info.phone_number
    source = TelecomCallerNameInfoSourceTypes.TWILIO

    telecom_caller_name_info.caller_name = caller_name
    telecom_caller_name_info.caller_name_type = caller_type
    telecom_caller_name_info.phone_number = phone_number
    telecom_caller_name_info.source = source

    log.info("Updated local model with twilio response data")
