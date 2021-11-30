from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from twilio.rest import Client

from core.models import AuditTrailModel
from calls.field_choices import (
    CallConnectionTypes,
    CallDirectionTypes,
    EngagementPersonaTypes,
    NonAgentEngagementPersonaTypes,
    ReferralSourceTypes,
    TelecomCallerNameInfoType,
    TelecomPersonaTypes,
)


class Call(AuditTrailModel):
    telecom_call_id = models.CharField(max_length=255)
    caller_audio_url = models.CharField(max_length=255)
    callee_audio_url = models.CharField(max_length=255)
    call_start_time = models.DateTimeField()
    call_end_time = models.DateTimeField()
    duration_seconds = models.DurationField()
    connect_duration_seconds = models.DurationField()
    progress_time_seconds = models.DurationField()
    call_direction = models.CharField(choices=CallDirectionTypes.choices, max_length=50, db_index=True)
    domain = models.ForeignKey(
        "auth.Group",
        on_delete=models.SET_NULL,
        verbose_name="The domain the call pertains to",
        related_name="calls",
        null=True,
    )
    sip_caller_number = PhoneNumberField()
    sip_caller_name = models.CharField(max_length=255, blank=True)
    sip_callee_number = PhoneNumberField()
    sip_callee_name = models.CharField(max_length=255, blank=True)
    checked_voicemail = models.BooleanField()
    went_to_voicemail = models.BooleanField()
    call_connection = models.CharField(choices=CallConnectionTypes.choices, max_length=50)
    who_terminated_call = models.CharField(choices=TelecomPersonaTypes.choices, max_length=50)
    referral_source = models.CharField(choices=ReferralSourceTypes.choices, max_length=50, blank=True)
    caller_type = models.CharField(choices=EngagementPersonaTypes.choices, max_length=50)
    callee_type = models.CharField(choices=EngagementPersonaTypes.choices, max_length=50)
    metadata_file_uri = models.CharField(max_length=255)


class AgentEngagedWith(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="The call engaged with", related_name="engaged_in_calls")
    non_agent_engagement_persona_type = models.CharField(choices=NonAgentEngagementPersonaTypes.choices, max_length=50, blank=True)


class CallLabel(AuditTrailModel):
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="The call being labeled", related_name="labeled_calls")
    metric = models.CharField(max_length=255, db_index=True)
    label = models.CharField(max_length=255, db_index=True)


class TelecomCallerNameInfoManager(models.Manager):


    # twilio lookup API: https://support.twilio.com/hc/en-us/articles/360050891214-Getting-Started-with-the-Twilio-Lookup-API
    # Example lookups in python: https://www.twilio.com/docs/lookup/api
    # API Explorer - "Lookup": https://console.twilio.com/us1/develop/api-explorer/endpoints?frameUrl=%2Fconsole%2Fapi-explorer%3Fx-target-region%3Dus1&currentFrameUrl=%2Fconsole%2Fapi-explorer%2Flookup%2Flookup-phone-numbers%2Ffetch%3F__override_layout__%3Dembed%26bifrost%3Dtrue%26x-target-region%3Dus1

    def get_or_create_from_twilio(self, **obj_data):
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # get phone number
        phone_number = obj_data.get("phone_number")
        print(phone_number)

        # modify phone number formatting (country code +1)

        # search database for record

        # check freshness / staleness of record
        # if exists and is still fresh, return record

        # lookup value in twilio
        phone_number_info = client.lookups.v1.phone_numbers("+14403644304").fetch(type=["caller-name", "carrier"])  # type is important otherwise we won't get the caller_name properties including caller_type

        # shape of the date
        # {
        #    "caller_name": {"caller_name": "", "caller_type", "error_code": ""}
        #    "carrier": {"mobile_country_code": "313", "mobile_network_code": "981", "name": "Bandwidth/13 - Bandwidth.com - SVR", "type": "voip", "error_code": None}
        #    "country_code": "",
        #    "phone_number": "",
        #    "national_format": "",
        #    "carrier"
        # }
        caller_name = phone_number_info.caller_name

        # caller_type, types: BUSINESS CONSUMER UNDETERMINED

        
        telcom_caller_name_info = TelecomCallerNameInfo(phone_number="14403544304", caller_name=caller_name["caller_name"])
        return telcom_caller_name_info
    

class TelecomCallerNameInfo(AuditTrailModel):
    phone_number = PhoneNumberField(db_index=True)
    caller_name = models.CharField(max_length=255)
    caller_name_type = models.CharField(choices=TelecomCallerNameInfoType.choices, max_length=50)

    objects = TelecomCallerNameInfoManager()
