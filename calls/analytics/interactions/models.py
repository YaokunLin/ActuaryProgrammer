import logging
from calls.analytics.interactions.field_choices import AgentInteractionMetricTypes
from core.abstract_models import AuditTrailModel
from django.db import models
from django_extensions.db.fields import ShortUUIDField

from core.models import Agent

# Get an instance of a logger
log = logging.getLogger(__name__)


class AgentCallScore(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="Interactions during the call", related_name="call_interactions")
    metric = models.CharField(choices=AgentInteractionMetricTypes.choices, max_length=180)
    score = models.FloatField()
    raw_model_run_id = models.CharField(max_length=22)
