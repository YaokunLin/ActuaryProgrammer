from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentInteractionMetricTypes(models.TextChoices):
    SCHEDULING_ACCOMMODATIONS = "scheduling_accommodations"
    REFERRAL_SOURCE = "referral_source"
    PROCEDURE_EXPLANATION = "procedure_explanation"
    PAYMENT_METHOD = "payment_method"
    PATIENT_DEMOGRAPHICS = "patient_demographics"
    GREETING = "greeting"
    AGENT_OVERTALK = "agent_overtalk"


class AgentInteractionMetricTypes(models.TextChoices):
    pass


class AgentInteractionOvertalkMetricTypes(models.TextChoices):
    NONE = "none"
    INFREQUENT = "infrequent"
    MODERATE = "moderate"
    FREQUENT = "frequent"
