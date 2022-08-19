from django.db import models
from django_extensions.db.fields import ShortUUIDField


from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from core.abstract_models import AuditTrailModel
from core.models import Agent

class AgentAssignedCall(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="assigned_calls")
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="Call assigned to agent", related_name="assigned_agent") 


class AgentEngagedWith(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    # TODO: rename this related name 'engaged_in_calls' to something that makes more sense
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="The call engaged with", related_name="engaged_in_calls")
    non_agent_engagement_persona_type = models.CharField(choices=NonAgentEngagementPersonaTypes.choices, max_length=50, blank=True)
    raw_non_agent_engagement_persona_model_run_id = models.CharField(max_length=22, blank=True) # Blankable - Sometimes we determine type via CNAM. Also to decouple this.
    non_agent_engagement_persona_model_run = models.ForeignKey(
        "ml.MLModelResultHistory",
        on_delete=models.SET_NULL,
        verbose_name="ml model run for this non agent engagement persona",
        related_name="resulting_non_agent_engagement_personas",
        null=True,
    )
