import datetime

from django.conf import settings
from django_countries.fields import CountryField
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField


from core.abstract_models import AuditTrailModel
from calls.field_choices import (
    CallAudioStatusTypes,
    CallConnectionTypes,
    CallDirectionTypes,
    EngagementPersonaTypes,
    NonAgentEngagementPersonaTypes,
    ReferralSourceTypes,
    SupportedAudioMimeTypes,
    TelecomCallerNameInfoSourceTypes,
    TelecomCallerNameInfoTypes,
    TelecomCarrierTypes,
    TelecomPersonaTypes,
)


class Call(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_start_time = models.DateTimeField()
    call_end_time = models.DateTimeField()
    duration_seconds = models.DurationField()
    connect_duration_seconds = models.DurationField(null=True)
    progress_time_seconds = models.DurationField(null=True)
    call_direction = models.CharField(choices=CallDirectionTypes.choices, max_length=50, db_index=True, blank=True)
    practice_telecom = models.ForeignKey(
        "core.PracticeTelecom",
        on_delete=models.SET_NULL,
        verbose_name="The practice telecom id the call pertains to",
        related_name="calls",
        null=True,
    )
    caller_id = models.ForeignKey("core.UserTelecom", on_delete=models.SET_NULL, null=True, related_name="calls_made")
    callee_id = models.ForeignKey("core.UserTelecom", on_delete=models.SET_NULL, null=True, related_name="calls_recieved")
    sip_caller_number = PhoneNumberField(blank=True)
    sip_caller_name = models.CharField(max_length=255, blank=True)
    sip_callee_number = PhoneNumberField(blank=True)
    sip_callee_name = models.CharField(max_length=255, blank=True)
    checked_voicemail = models.BooleanField(null=True)
    went_to_voicemail = models.BooleanField(null=True)
    call_connection = models.CharField(choices=CallConnectionTypes.choices, max_length=50, blank=True)
    who_terminated_call = models.CharField(choices=TelecomPersonaTypes.choices, max_length=50, blank=True)
    referral_source = models.CharField(choices=ReferralSourceTypes.choices, max_length=50, blank=True)
    caller_type = models.CharField(choices=EngagementPersonaTypes.choices, max_length=50, blank=True)
    callee_type = models.CharField(choices=EngagementPersonaTypes.choices, max_length=50, blank=True)
    metadata_file_uri = models.CharField(max_length=255, blank=True)  # Planning to deprecate


class CallAudioPartial(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE)
    mime_type = models.CharField(choices=SupportedAudioMimeTypes.choices, max_length=180)
    status = models.CharField(choices=CallAudioStatusTypes.choices, max_length=80, default=CallAudioStatusTypes.RETRIEVAL_FROM_PROVIDER_IN_PROGRESS)

    @property
    def signed_url(
        self,
        client: str = settings.CLOUD_STORAGE_CLIENT,
        bucket: str = settings.CALL_AUDIO_BUCKET,
        expiration: datetime.timedelta = settings.SIGNED_STORAGE_URL_EXPIRATION_DELTA,
    ) -> str:
        bucket = client.get_bucket(bucket)
        blob = bucket.get_blob(self.id)
        return blob.generate_signed_url(expiration=expiration)


class AgentEngagedWith(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="The call engaged with", related_name="engaged_in_calls")
    non_agent_engagement_persona_type = models.CharField(choices=NonAgentEngagementPersonaTypes.choices, max_length=50, blank=True)


class CallLabel(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="The call being labeled", related_name="labeled_calls")
    metric = models.CharField(max_length=255, db_index=True)
    label = models.CharField(max_length=255, db_index=True)


class TelecomCallerNameInfo(AuditTrailModel):
    phone_number = PhoneNumberField(primary_key=True)
    caller_name = models.CharField(max_length=255, blank=True, null=False, default="", db_index=True)
    caller_name_type = models.CharField(choices=TelecomCallerNameInfoTypes.choices, max_length=50, blank=True, null=False, default="")
    country_code = CountryField(blank=True, default="US")  # ISO 3166-1 alpha-2 and countr
    source = models.CharField(choices=TelecomCallerNameInfoSourceTypes.choices, max_length=50, blank=True, null=False, default="")

    carrier_name = models.CharField(max_length=255, blank=True, null=False, default="")
    carrier_type = models.CharField(choices=TelecomCarrierTypes.choices, max_length=50, blank=True, null=False, default="")

    # the following are used together to identify a mobile network operator
    mobile_country_code = models.IntegerField(max_length=3, null=True, default=None)  # 3 digit mobile country code of the carrier
    mobile_network_code = models.IntegerField(max_length=3, null=True, default=None)  # 2-3 digit mobile network code of the carrier, (only for mobile numbers)

    extract_raw_json = models.JSONField(default=None, null=True)  # raw value used to generate this, if received

    def is_caller_name_info_stale(self) -> bool:
        time_zone = self.modified_at.tzinfo  # use database standard timezone
        today = datetime.datetime.now(time_zone)  # today by the database's standard
        expiration_time = self.modified_at + datetime.timedelta(seconds=settings.TELECOM_CALLER_NAME_INFO_MAX_AGE_IN_SECONDS)  # calculate expiration time

        return today > expiration_time