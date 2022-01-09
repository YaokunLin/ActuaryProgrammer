from django.conf import settings
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import AuditTrailModel
from .field_choices import MESSAGE_STATUSES, MESSAGE_PRIORITIES, MESSAGE_PRIORITIES_DEFAULT


class SMSMessage(AuditTrailModel):
    id = models.CharField(primary_key=True, editable=False, max_length=255)  # using telecom's sent short uuid
    patient = models.ForeignKey("core.Patient", on_delete=models.SET_NULL, null=True)
    assigned_to_agent = models.ForeignKey("core.Agent", on_delete=models.SET_NULL, null=True)
    owner = PhoneNumberField()
    source_number = PhoneNumberField(blank=True)
    destination_number = PhoneNumberField(blank=True)
    error_code = models.IntegerField(null=True)
    to_numbers = models.JSONField()
    from_number = PhoneNumberField()
    text = models.CharField(max_length=2048)
    message_status = models.CharField(choices=MESSAGE_STATUSES, blank=True, max_length=255)
    sent_date_time = models.DateTimeField()
    delivered_date_time = models.DateTimeField(null=True)
    direction = models.CharField(max_length=255)
    media = models.JSONField(null=True)
    segment_count = models.IntegerField(null=True)
    priority = models.CharField(choices=MESSAGE_PRIORITIES, default=MESSAGE_PRIORITIES_DEFAULT, max_length=255)
    expiration = models.DateTimeField(null=True)
    tag = models.CharField(max_length=180)

    @property
    def application_id(self):
        settings.BANDWIDTH_APPLICATION_ID
