import logging
import re

from django.conf import settings
from django.db import DatabaseError
from django.http import Http404, HttpResponseBadRequest
from phonenumber_field.modelfields import to_python as to_phone_number
from rest_framework import viewsets
from rest_framework.response import Response
from twilio.base.exceptions import TwilioException

from calls.twilio_etl import (
    get_caller_name_info_from_twilio,
    update_telecom_caller_name_info_with_twilio_data_for_valid_sections,
)
from .field_choices import (
    TelecomCallerNameInfoSourceTypes,
    TelecomCallerNameInfoTypes,
)
from .models import (
    Call,
    CallLabel,
    TelecomCallerNameInfo,
)
from .serializers import (
    CallLabelSerializer,
    CallSerializer,
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

        try:
            phone_number = TelecomCallerNameInfoViewSet.validate_and_normalize_phone_number(phone_number_raw=phone_number_raw)
        except Exception as e:
            return HttpResponseBadRequest(f"Invalid phone number detected, phone_number_raw: '{phone_number_raw}'")

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

        # certain area codes are always business numbers if configured
        us_area_code = get_us_area_code(phone_number)
        log.info(
            f"Checking area code: '{us_area_code}' from phone_number: '{phone_number}' against known business telecom area codes: '{settings.TELECOM_AREA_CODES_TO_MARK_AS_BUSINESS_NUMBERS}'"
        )
        if us_area_code in settings.TELECOM_AREA_CODES_TO_MARK_AS_BUSINESS_NUMBERS:
            log.info(f"Area code is a known business area code for phone_number: '{phone_number}'")
            telecom_caller_name_info.source = TelecomCallerNameInfoSourceTypes.PEERLOGIC
            telecom_caller_name_info.caller_name_type = TelecomCallerNameInfoTypes.BUSINESS
            telecom_caller_name_info.save()
            return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

        # fetch from twilio and update database
        try:
            # get and validate twilio data
            log.info(f"Twilio is on and we have stale / expired or missing data. Requesting data from twilio for phone_number: '{phone_number}'")
            twilio_caller_name_info = get_caller_name_info_from_twilio(phone_number=phone_number)

            # update local object
            log.info(f"Extracting and transforming data from twilio for phone_number: '{phone_number}'.")
            update_telecom_caller_name_info_with_twilio_data_for_valid_sections(telecom_caller_name_info, twilio_caller_name_info)

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
        if created and (telecom_caller_name_info.caller_name_type is "" and telecom_caller_name_info.telecom_caller_name_info.carrier_type is ""):
            log.warn(
                f"Incompleted caller_name_info record. No stale or fresh caller_name_info data is available. We've created a new caller_name_info object but couldn't fill it with Twilio values. ROLLING BACK. phone_number: '{phone_number}'"
            )
            telecom_caller_name_info.delete()
            log.warn(f"ROLLED BACK / DELETED incomplete record for phone_number: '{phone_number}'")
            raise Http404

        # win
        log.info(f"caller_name_info available to send to client for '{phone_number}'")
        return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

    @classmethod
    def validate_and_normalize_phone_number(cls, phone_number_raw: str) -> str:
        # validate and normalize phone number
        log.info(f"Validating phone number: phone_number_raw: '{phone_number_raw}'")

        # first level of normalization because we're generous with our input
        phone_number_raw = re.sub("[^0-9]", "", phone_number_raw)  # remove non-digits
        phone_number_raw = f"+{phone_number_raw}"  # add preceding plus sign

        # first validation
        phone_number = to_phone_number(phone_number_raw)  # this will explode for obviously bad phone numbers
        if not phone_number.is_valid():  # true for not so obviously bad phone numbers
            msg = f"Invalid phone number detected, phone_number_raw: '{phone_number_raw}'"
            log.error(msg)
            raise TypeError(msg)

        # be aware strange phone numbers will survive the above
        # strange phone numbers from the above include ones where a phone number has letters appended: 14401234567bb
        # strange phone numbers like this will be accepted by twilio which will truncate the bad parts
        # we MUST normalize to get something reasonable-looking for our system's storage, reduce duplicates, and reduce costs
        log.info(f"Normalizing phone_number_raw: '{phone_number_raw}'")
        phone_number = phone_number.as_e164
        log.info(f"Normalized phone_number_raw: '{phone_number_raw}' to phone_number: '{phone_number}'")

        return phone_number


def get_us_area_code(us_phone_number_in_e164: str) -> str:
    # number: +1 [234] 567 8910
    # index:  01  234  5(exclusive)
    example_phone_number = "+12345678910"
    us_phone_number_in_e164_length = len(example_phone_number)
    if len(us_phone_number_in_e164) != us_phone_number_in_e164_length:
        # this should never occur if we're using this at the appropriate point in the code
        raise TypeError(f"Invalid normalized us phone_number: '{us_phone_number_in_e164}' detected. Function used erroneously.")

    return us_phone_number_in_e164[2:5]
