import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from twilio.rest.lookups.v1.phone_number import PhoneNumberInstance
from rest_framework import viewsets
from rest_framework.response import Response
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
    lookup_field = "phone_number"


    def retrieve(self, request, phone_number):
        print("hello")
        if not settings.TWILIO_IS_ENABLED:
            return super().retrieve(request, phone_number)

        # modify phone number formatting (country code +1)
        
        # search database for record
        telecom_caller_name_info = get_or_none(TelecomCallerNameInfo, phone_number=phone_number)

        if telecom_caller_name_info and not telecom_caller_name_info.is_caller_name_info_stale():
            # TODO log 
            print("exists and is not stale")
            return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

        print("IT' STALE!")
        # fetch from twilio
        twilio_caller_name_info = get_caller_name_info_from_twilio(phone_number=phone_number)
        
        # create object
        telecom_caller_name_info = convert_twilio_phone_number_info_to_telecom_caller_name_info(twilio_caller_name_info)

        # save
        telecom_caller_name_info.save()

        # return
        return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)


def get_or_none(classmodel, **kwargs):
    try:
        return classmodel.objects.get(**kwargs)
    except classmodel.MultipleObjectsReturned as e:
        # TODO: explode
        pass
    except classmodel.DoesNotExist:
        return None


def convert_twilio_phone_number_info_to_telecom_caller_name_info(twilio_phone_number_info: PhoneNumberInstance) -> TelecomCallerNameInfo:
    # twilio lookup API: https://support.twilio.com/hc/en-us/articles/360050891214-Getting-Started-with-the-Twilio-Lookup-API
    # Example lookups in python: https://www.twilio.com/docs/lookup/api
    # API Explorer - "Lookup": https://console.twilio.com/us1/develop/api-explorer/endpoints?frameUrl=%2Fconsole%2Fapi-explorer%3Fx-target-region%3Dus1&currentFrameUrl=%2Fconsole%2Fapi-explorer%2Flookup%2Flookup-phone-numbers%2Ffetch%3F__override_layout__%3Dembed%26bifrost%3Dtrue%26x-target-region%3Dus1

    # shape of the date
    # {
    #    "caller_name": {"caller_name": "", "caller_type", "error_code": ""}
    #    "carrier": {"mobile_country_code": "313", "mobile_network_code": "981", "name": "Bandwidth/13 - Bandwidth.com - SVR", "type": "voip", "error_code": None}
    #    "country_code": "",
    #    "phone_number": "",
    #    "national_format": ""
    # }
    # TODO debug log
    print(twilio_phone_number_info.__dict__)

    caller_name_section = twilio_phone_number_info.caller_name
    if caller_name_section is None:
        # TODO explode
        return None

    caller_name = caller_name_section.get("caller_name", None)
    caller_type = caller_name_section.get("caller_type", "")  # BUSINESS CONSUMER UNDETERMINED
    caller_type = caller_type.lower()
    if caller_type not in TelecomCallerNameInfoTypes.values:
        caller_type = None
    phone_number = twilio_phone_number_info.phone_number
    source = TelecomCallerNameInfoSourceTypes.TWILIO

    telcom_caller_name_info = TelecomCallerNameInfo(phone_number=phone_number, caller_name=caller_name, caller_name_type=caller_type, source=source)
    return telcom_caller_name_info


def get_caller_name_info_from_twilio(phone_number, client=None):
    if not client:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # lookup value in twilio
    phone_number_info = client.lookups.v1.phone_numbers(phone_number).fetch(type=["caller-name", "carrier"])  # you must specify the types whose values you want to have filled in, otherwise they will be None
    return phone_number_info
