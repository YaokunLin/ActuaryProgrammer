from django.db import models
from django.utils.translation import gettext_lazy as _


class EngagementPersonaTypes(models.TextChoices):
    AGENT = "agent"
    NON_AGENT = "non_agent"


class NonAgentEngagementPersonaTypes(models.TextChoices):
    NEW_PATIENT = "new_patient"
    EXISTING_PATIENT = "existing_patient"
    CONTRACTOR_VENDOR = "contractor_vendor"
    INSURANCE_PROVIDER = "insurance_provider"
    OTHERS = "others"
