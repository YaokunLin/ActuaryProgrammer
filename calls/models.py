import datetime

from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from django_userforeignkey.models.fields import UserForeignKey
from phonenumber_field.modelfields import PhoneNumberField


from core.models import AuditTrailModel
from calls.field_choices import (
    CallConnectionTypes,
    CallDirectionTypes,
    EngagementPersonaTypes,
    NonAgentEngagementPersonaTypes,
    ReferralSourceTypes,
    TelecomCallerNameInfoTypes,
    TelecomCallerNameInfoSourceTypes,
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

class TelecomCallerNameInfo(AuditTrailModel):
    id = None
    phone_number = PhoneNumberField(primary_key=True)
    caller_name = models.CharField(max_length=255)
    caller_name_type = models.CharField(choices=TelecomCallerNameInfoTypes.choices, max_length=50, null=True)
    source = models.CharField(choices=TelecomCallerNameInfoSourceTypes.choices, max_length=50)

    # created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # modified_at = models.DateTimeField(auto_now=True, db_index=True)
    # created_by = UserForeignKey(
    #     on_delete=models.SET_NULL,
    #     auto_user_add=True,
    #     verbose_name="The user that is automatically assigned",
    #     related_name="%(class)s_created",
    #     blank=True,
    #     null=True,
    # )
    # modified_by = UserForeignKey(
    #     on_delete=models.SET_NULL,
    #     auto_user_add=True,
    #     verbose_name="The user that is automatically assigned",
    #     related_name="%(class)s_modified",
    #     blank=True,
    #     null=True,
    # )

    # class Meta:
    #     get_latest_by = "modified_at"


    def is_caller_name_info_stale(self) -> bool:
        time_zone = self.modified_at.tzinfo  # use database standard timezone
        today = datetime.datetime.now(time_zone)  # today by the database's standard
        expiration_time = self.modified_at + datetime.timedelta(seconds=settings.TELECOM_CALLER_NAME_INFO_MAX_AGE_IN_SECONDS)  # calculate expiration time
        
        return today > expiration_time
