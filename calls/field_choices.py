from django.db import models


class EngagementPersonaTypes(models.TextChoices):
    AGENT = "agent"
    NON_AGENT = "non_agent"


class NonAgentEngagementPersonaTypes(models.TextChoices):
    NEW_PATIENT = "new_patient"
    EXISTING_PATIENT = "existing_patient"
    CONTRACTOR_VENDOR = "contractor_vendor"
    INSURANCE_PROVIDER = "insurance_provider"
    OTHERS = "others"


class CallConnectionTypes(models.TextChoices):
    MISSED = "missed"
    CONNECTED = "connected"


class TelecomPersonaTypes(models.TextChoices):
    CALLER = "caller"
    CALLEE = "callee"


class ReferralSourceTypes(models.TextChoices):
    PATIENT_REFERRAL = "patient_referral"
    MEDICAL_PROVIDER = "medical_provider"
    DENTAL_PROVIDER = "dental_provider"
    WEB_SEARCH = "web_search"
    SOCIAL_MEDIA = "social_media"
    INSURANCE = "insurance"
    PAID_ADVERTISING = "paid_advertising"
    NOT_APPLICABLE = "not_applicable"
    OTHERS = "others"


class CallDirectionTypes(models.TextChoices):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class TelecomCallerNameInfoTypes(models.TextChoices):
    PERSONAL = "individual"
    BUSINESS = "business"
