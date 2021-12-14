from django.db import models
from django.conf import settings

from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel
from .managers import CadenceManager
from .field_choices import CADENCES


class Cadence(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    client = models.ForeignKey("core.Client", on_delete=models.CASCADE)
    telecom_user_sending_reminder = models.ForeignKey(
        "core.UserTelecom",
        on_delete=models.SET_NULL,
        verbose_name="The telecom user that is sending the reminder",
        related_name="cadences",
        null=True,
    )
    cadence_type = models.CharField(max_length=40, choices=CADENCES)

    objects = CadenceManager()
