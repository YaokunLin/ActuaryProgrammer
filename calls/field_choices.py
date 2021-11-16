from django.db import models


class PersonaTypes(models.TextChoices):
    NEW_PATIENT = "new_patient"
    EXISTING_PATIENT = "existing_patient"
    CONTRACTOR_VENDOR = "contractor_vendor"
    AGENT = "agent"


class CallConnectionTypes(models.TextChoices):
    MISSED = "missed"
    CONNECTED = "connected"


class WhoTerminatedCallTypes(models.TextChoices):
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
    UNKNOWN = "unknown"
    OTHER = "other"

class CallDirectionTypes(models.TextChoices):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"