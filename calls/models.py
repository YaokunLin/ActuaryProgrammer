from django.db import models

from phonenumber_field.modelfields import PhoneNumberField

from core.models import AuditTrailModel
from calls.field_choices import CallConnectionTypes, CallDirectionTypes, EngagementPersonaTypes, NonAgentTypes, ReferralSourceTypes, TelecomPersonaTypes


class Call(AuditTrailModel):
    telecom_call_id = models.CharField(max_length=255)
    caller_audio_url = models.CharField(max_length=255)
    callee_audio_url = models.CharField(max_length=255)
    call_start = models.DateTimeField()
    call_end = models.DateTimeField()
    duration_seconds = models.DurationField()
    connect_duration_seconds = models.DurationField()
    progress_time_seconds = models.DurationField()
    call_direction = models.CharField(choices=CallDirectionTypes.choices, max_length=50)
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
    agent_engaged_with = models.CharField(choices=NonAgentTypes.choices, max_length=50, blank=True)
    metadata_file_uri = models.CharField(max_length=255)


class CallLabel(AuditTrailModel):
    metric = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
