import logging
from calls.analytics.interactions.field_choices import AgentInteractionMetricTypes
from core.abstract_models import AuditTrailModel
from django.db import models
from django_extensions.db.fields import ShortUUIDField

from core.models import Agent

# Get an instance of a logger
log = logging.getLogger(__name__)


class AgentCallScoreMetricGroup(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    group_name = models.CharField(max_length=120)


class AgentCallScoreMetric(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    metric = models.CharField(choices=AgentInteractionMetricTypes.choices, max_length=180)
    metric_human_readable = models.CharField(max_length=120)  # be aware this is for display purposes so lengths should be reasonable
    group = models.ForeignKey(AgentCallScoreMetricGroup, on_delete=models.CASCADE, related_name="agent_call_score_metrics")



class AgentCallScore(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="Interactions during the call", related_name="call_interactions")
    metric = models.ForeignKey(AgentCallScoreMetric, on_delete=models.CASCADE, related_name="agent_call_scores")
    score = models.FloatField()
    raw_model_run_id = models.CharField(max_length=22)
    