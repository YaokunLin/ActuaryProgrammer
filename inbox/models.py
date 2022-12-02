import shortuuid
from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import AuditTrailModel

from .field_choices import MessagePriorities, PeerlogicMessageStatuses


class SMSMessage(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    bandwidth_id = models.CharField(editable=False, max_length=255, default=shortuuid.uuid)
    # TODO: put in the bandwidth description in the datamodel
    patient = models.ForeignKey("core.Patient", on_delete=models.SET_NULL, null=True)
    assigned_to_agent = models.ForeignKey("core.Agent", on_delete=models.SET_NULL, null=True)
    owner = PhoneNumberField()
    destination_number = PhoneNumberField(blank=True)
    error_code = models.IntegerField(null=True)
    to_numbers = models.JSONField()
    from_number = PhoneNumberField()
    text = models.CharField(max_length=2048)
    message_status = models.CharField(choices=PeerlogicMessageStatuses.choices, blank=True, max_length=255)
    sent_date_time = models.DateTimeField(null=True)
    delivered_date_time = models.DateTimeField(null=True)
    errored_date_time = models.DateTimeField(null=True)
    error_message = models.CharField(max_length=180, blank=True)
    direction = models.CharField(max_length=255)
    media = models.JSONField(null=True)
    segment_count = models.IntegerField(null=True)
    priority = models.CharField(choices=MessagePriorities.choices, default=MessagePriorities.DEFAULT, max_length=255)
    expiration = models.DateTimeField(null=True)
    tag = models.CharField(max_length=180)

    @property
    def application_id(self):
        settings.BANDWIDTH_APPLICATION_ID
