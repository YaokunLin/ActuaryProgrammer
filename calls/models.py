import logging
from datetime import datetime, timedelta
from typing import Optional

from core.abstract_models import AuditTrailModel
from django.conf import settings
from django.db import models
from django_countries.fields import CountryField
from django_extensions.db.fields import ShortUUIDField
from gcloud.storage import Client, Bucket
from phonenumber_field.modelfields import PhoneNumberField

from calls.analytics.intents.models import (CallOutcome, CallOutcomeReason, CallPurpose)
from calls.field_choices import (
    CallAudioFileStatusTypes,
    CallConnectionTypes,
    CallDirectionTypes,
    CallTranscriptFileStatusTypes,
    EngagementPersonaTypes,
    NonAgentEngagementPersonaTypes,
    ReferralSourceTypes,
    SpeechToTextModelTypes,
    SupportedAudioMimeTypes,
    SupportedTranscriptMimeTypes,
    TelecomCallerNameInfoSourceTypes,
    TelecomCallerNameInfoTypes,
    TelecomCarrierTypes,
    TelecomPersonaTypes,
    TranscriptTypes,
)
from core.cloud_storage_helpers import get_signed_url
from core.models import PracticeTelecom

# Get an instance of a logger
log = logging.getLogger(__name__)


class Call(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_start_time = models.DateTimeField()
    call_end_time = models.DateTimeField()
    duration_seconds = models.DurationField()
    connect_duration_seconds = models.DurationField(null=True)
    progress_time_seconds = models.DurationField(null=True)
    call_direction = models.CharField(choices=CallDirectionTypes.choices, max_length=50, db_index=True, blank=True)
    practice = models.ForeignKey(
        "core.Practice",
        on_delete=models.CASCADE,
        verbose_name="The practice that made or received the call",
        related_name="calls",
        null=False,
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

    # TODO: Remove domain everywhere and use practice_id
    # Dependencies:
    #   - peerlogic-ml-stream-pipeline
    #   - peerlogic-ml-rest-api
    #   - analytics-dashboard
    @property
    def domain(self) -> str:
        practice_telecom = PracticeTelecom.objects.get(practice=self.practice)
        return practice_telecom.domain


class CallAudio(AuditTrailModel):
    BUCKET_NAME: str = settings.BUCKET_NAME_CALL_AUDIO
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE)
    mime_type = models.CharField(choices=SupportedAudioMimeTypes.choices, max_length=180)
    status = models.CharField(choices=CallAudioFileStatusTypes.choices, max_length=80, default=CallAudioFileStatusTypes.RETRIEVAL_FROM_PROVIDER_IN_PROGRESS)

    @property
    def signed_url(self) -> Optional[str]:
        return get_signed_url(filename=self.id, bucket_name=self.BUCKET_NAME)


class CallTranscript(AuditTrailModel):
    BUCKET_NAME: str = settings.BUCKET_NAME_CALL_TRANSCRIPT
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE)
    publish_event_on_patch = models.BooleanField(default=False)
    mime_type = models.CharField(choices=SupportedTranscriptMimeTypes.choices, max_length=180, default=SupportedTranscriptMimeTypes.TEXT_PLAIN)
    transcript_type = models.CharField(choices=TranscriptTypes.choices, max_length=80, default=TranscriptTypes.FULL_TEXT)
    speech_to_text_model_type = models.CharField(choices=SpeechToTextModelTypes.choices, max_length=80, default=SpeechToTextModelTypes.GOOGLE)
    status = models.CharField(
        choices=CallTranscriptFileStatusTypes.choices, max_length=80, default=CallTranscriptFileStatusTypes.RETRIEVAL_FROM_PROVIDER_IN_PROGRESS
    )

    @property
    def file_basename(self) -> str:
        return f"{self.id}_{self.transcript_type}.txt"

    @property
    def signed_url(self) -> Optional[str]:
        return get_signed_url(filename=self.file_basename, bucket_name=self.BUCKET_NAME)


class CallPartial(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE)
    # TODO: sip_callee_extension?
    # TODO: sip_caller_extension?
    time_interaction_started = models.DateTimeField()
    time_interaction_ended = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["call", "time_interaction_started", "time_interaction_ended"], name="unique time constraints for every call")
        ]


class CallAudioPartial(AuditTrailModel):
    BUCKET_NAME: str = settings.BUCKET_NAME_CALL_AUDIO_PARTIAL
    id = ShortUUIDField(primary_key=True, editable=False)
    call_partial = models.ForeignKey(CallPartial, on_delete=models.CASCADE, related_name="call_audio_partials")
    mime_type = models.CharField(choices=SupportedAudioMimeTypes.choices, max_length=180)
    status = models.CharField(choices=CallAudioFileStatusTypes.choices, max_length=80, default=CallAudioFileStatusTypes.RETRIEVAL_FROM_PROVIDER_IN_PROGRESS)

    @property
    def signed_url(self) -> Optional[str]:
        return get_signed_url(filename=self.id, bucket_name=self.BUCKET_NAME)


class CallTranscriptPartial(AuditTrailModel):
    BUCKET_NAME: str = settings.BUCKET_NAME_CALL_TRANSCRIPT_PARTIAL
    id = ShortUUIDField(primary_key=True, editable=False)
    call_partial = models.ForeignKey(CallPartial, on_delete=models.CASCADE)
    call_audio_partial = models.ForeignKey(CallAudioPartial, on_delete=models.SET_NULL, null=True)
    mime_type = models.CharField(choices=SupportedTranscriptMimeTypes.choices, max_length=180, default=SupportedTranscriptMimeTypes.TEXT_PLAIN)
    transcript_type = models.CharField(choices=TranscriptTypes.choices, max_length=80, default=TranscriptTypes.FULL_TEXT)
    speech_to_text_model_type = models.CharField(choices=SpeechToTextModelTypes.choices, max_length=80, default=SpeechToTextModelTypes.GOOGLE)
    status = models.CharField(
        choices=CallTranscriptFileStatusTypes.choices, max_length=80, default=CallTranscriptFileStatusTypes.RETRIEVAL_FROM_PROVIDER_IN_PROGRESS
    )

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, *args):
        if self.call_audio_partial and self.call_audio_partial.call_partial != self.call_partial:
            raise ValueError("call_audio_partial's call_partial and this object's call_partial must match. Not saving.")
        super().save(force_insert, force_update, using, update_fields)

    @property
    def file_basename(self) -> str:
        return f"{self.id}_{self.transcript_type}.txt"

    @property
    def signed_url(self) -> Optional[str]:
        return get_signed_url(filename=self.file_basename, bucket_name=self.BUCKET_NAME)


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
        today = datetime.now(time_zone)  # today by the database's standard
        expiration_time = self.modified_at + timedelta(seconds=settings.TELECOM_CALLER_NAME_INFO_MAX_AGE_IN_SECONDS)  # calculate expiration time

        return today > expiration_time
