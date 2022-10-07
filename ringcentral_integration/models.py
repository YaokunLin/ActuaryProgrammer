from django.db import models
from django.urls import reverse

from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class RingCentralAPICredentials(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    voip_provider = models.ForeignKey("core.VoipProvider", on_delete=models.CASCADE)
    
    api_url = models.CharField(max_length=2048, blank=True)
    client_id = models.CharField(max_length=64, blank=True)
    client_secret = models.CharField(max_length=64, blank=True)
    username = models.CharField(max_length=63, blank=True)
    password = models.CharField(max_length=255, blank=True)

    active = models.BooleanField(null=True, blank=False, default=False)  # whether these credentials are active for usage

    class Meta:
        verbose_name_plural = "RingCentralAPICredentials"

class RingCentralCallSubscription(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    source_id = models.CharField(
        max_length=32, blank=True, default="", help_text=("Subscription ID for RingCentral on the Voip Provider's side. The source of the data / events")
    )
    practice_telecom = models.ForeignKey("core.PracticeTelecom", null=True, on_delete=models.SET_NULL)  # keep call subscriptions and their ids forever

    active = models.BooleanField(null=True, blank=False, default=True)  # call subscription is active and should be receiving data

    @property
    def call_subscription_uri(self):
        return reverse("ringcentral:call-subscription-event-receiver", kwargs={"practice_telecom_id": self.practice_telecom.pk, "call_subscription_id": self.id})

class RingCentralSessionEvent(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)
    sequence = models.IntegerField(null=True, default=None)
    session_id = models.CharField(null=False, blank=False, max_length=255)
    telephony_session_id = models.CharField(null=False, blank=False, max_length=255)
    server_id = models.CharField(null=False, blank=False, max_length=255)
    event_time = models.DateTimeField(null=False)
    to_name = models.CharField(null=True, max_length=255)
    to_extension_id = models.CharField(null=True, max_length=255)
    to_phone_number = models.CharField(null=True, max_length=255)
    from_name = models.CharField(null=True, max_length=255)
    from_extension_id = models.CharField(null=True, max_length=255)
    from_phone_number = models.CharField(null=True, max_length=255)
    muted = models.BooleanField(default=False)
    status_rcc = models.BooleanField(default=False)
    status_code = models.CharField(null=False, blank=False, max_length=255)
    status_reason = models.CharField(null=True, max_length=255)
    account_id = models.CharField(null=False, blank=False, max_length=255)
    direction = models.CharField(null=False, blank=False, max_length=255)
    missed_call = models.BooleanField(default=False)
    stand_alone = models.BooleanField(default=False)
    full_session_event = models.JSONField(default=dict)

class RingCentralCallLeg(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)
    peerlogic_call_id = models.CharField(
        blank=True, default="", max_length=22, db_index=True
    )  # maps to calls/models.py Call model's id (non-fk to keep these segregated)
    action = models.CharField(null=True, blank=True, max_length=255)
    direction = models.CharField(null=True, blank=True, max_length=255)
    delegate_id = models.CharField(null=True, blank=True, max_length=255)
    delegate_name = models.CharField(null=True, blank=True, max_length=255)
    extension_id = models.CharField(null=True, blank=True, max_length=255)
    duration = models.IntegerField(null=True, default=None)
    extension_id = models.CharField(null=True, blank=True, max_length=255)
    extension_uri = models.CharField(null=True, blank=True, max_length=255)
    leg_type = models.CharField(null=True, blank=True, max_length=255)
    start_time = models.DateTimeField(null=False)
    type = models.CharField(null=True, blank=True, max_length=255)
    result = models.CharField(null=True, blank=True, max_length=255)
    reason = models.CharField(null=True, blank=True, max_length=255)
    reason_description = models.CharField(null=True, blank=True, max_length=255)
    to_name = models.CharField(null=True, max_length=255)
    to_extension_id = models.CharField(null=True, max_length=255)
    to_phone_number = models.CharField(null=True, max_length=255)
    from_name = models.CharField(null=True, max_length=255)
    from_extension_id = models.CharField(null=True, max_length=255)
    from_phone_number = models.CharField(null=True, max_length=255)
    transport = models.CharField(null=True, blank=True, max_length=255)
    recording = models.CharField(
        blank=True, default="", max_length=22, db_index=True
    )
    master = models.BooleanField(default=False)
    message_type = models.CharField(null=True, max_length=255)
    telephony_session_id = models.CharField(null=True, max_length=255)
    internal_type = models.CharField(null=True, max_length=255)