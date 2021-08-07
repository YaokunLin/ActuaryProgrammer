from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from .field_choices import MESSAGE_STATUSES, MESSAGE_PRIORITIES, MESSAGE_PRIORITIES_DEFAULT

class Contact(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    first_name = models.CharField(blank=True, max_length=255)
    last_name = models.CharField(blank=True, max_length=255)
    placeholder = models.CharField(blank=True, max_length=255)
    mobile_number = PhoneNumberField()
    fax_number = PhoneNumberField(blank=True)
    address_line_1 = models.CharField(blank=True, max_length=255)
    address_line_2 = models.CharField(blank=True, max_length=255)
    zip_code = models.CharField(max_length=255)


class SMSMessage(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=255)
    contact = models.ForeignKey("Contact", on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True)
    owner = PhoneNumberField()
    source_number = PhoneNumberField()
    destination_number = PhoneNumberField()
    error_code = models.IntegerField(null=True)
    to_numbers = models.JSONField()
    from_numbers = models.JSONField()
    text = models.CharField(max_length=2048)
    message_status = models.CharField(choices=MESSAGE_STATUSES, blank=True, max_length=255)
    from_date_time = models.DateTimeField()
    to_date_time = models.DateTimeField()
    direction = models.CharField(max_length=255)
    media = models.JSONField(null=True)
    segment_count = models.IntegerField(null=True)
    priority = models.CharField(choices=MESSAGE_PRIORITIES, default=MESSAGE_PRIORITIES_DEFAULT, max_length=255)
    expiration = models.DateTimeField(null=True)

    @property
    def application_id():
        settings.BANDWIDTH_APPLICATION_ID
