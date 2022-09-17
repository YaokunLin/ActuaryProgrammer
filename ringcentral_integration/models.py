from django.db import models
from django_extensions.db.fields import ShortUUIDField

from django.db import models


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
