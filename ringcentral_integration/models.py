from django.db import models
from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel

# Create your models here.
class RingCentralSessionEvent(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    sequence = models.CharField(null=False, blank=False, max_length=255)
    session_id = models.CharField(null=False, blank=False, max_length=255)
    telephony_session_id = models.CharField(null=False, blank=False, max_length=255)
    server_id = models.CharField(null=False, blank=False, max_length=255)
    event_time = models.DateTimeField(null=False)
    parties = models.JSONField(default=dict)
