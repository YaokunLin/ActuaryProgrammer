from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentInteractionGroupType(models.TextChoices):
    INTRO = "Introduction"
    SURVEY = "Survey"
    SELLING = "Selling"
    RAPPORT = "Rapport"
    CONVERT = "Convert"


class AgentInteractionMetricTypes(models.TextChoices):
    # Intro
    GREETING = "GREETING", _("Clear Well Spoken Greeting")
    ANNOUNCED_NAME = "ANNOUNCED_NAME", _("Announced Name")
    OFFERED_ASSISTANCE = "OFFERED_ASSISTANCE", _("Offered Assistance")
    STATED_BUSINESS_NAME = "STATED_BUSINESS_NAME", _("Stated Business Name")
    
    # Survey
    ASKED_PATIENT_NAME = "ASKED_PATIENT_NAME", _("Asked for the Patient's Name")
    ASKED_PATIENT_CONTACT_INFO = "ASKED_PATIENT_CONTACT_INFO", _("Asked for the Patient's Contact Information")
    ASKED_PATIENT_PURPOSE = "ASKED_PATIENT_PURPOSE", _("Asked for the Patient's Purpose")
    ASKED_REFERRING_SOURCE = "ASKED_REFERRING_SOURCE", _("Asked About Referring Source")

    # Selling
    MENTIONED_PROCEDURE = "MENTIONED_PROCEDURE", _("Mentioned Procedure Information")
    MENTIONED_INSURANCE_COVERAGE = "MENTIONED_INSURANCE_COVERAGE", _("Mentioned Insurance Coverage")
    MENTIONED_FINANCING = "MENTIONED_FINANCING", _("Mentioned Financing / Discount Club / Payment Plans")
    OFFERED_FREE_CONSULTATION = "OFFERED_FREE_CONSULTATION", _("Offered a Free Consultation")
    
    # Rapport
    AGENT_OVERTALK = "AGENT_OVERTALK", _("Listened Enough (Limited Overtalk)")
    HOLD_TIME = "HOLD_TIME", _("Acceptable Hold Time Length")
    ASKED_ABOUT_DISCOMFORT = "ASKED_ABOUT_DISCOMFORT", _("Asked About Discomfort")
    MENTIONED_PRICING = "MENTIONED_PRICING", _("Mentioned Pricing")
    
    # Convert
    OFFERED_APPOINTMENT_DATE_TIME = "OFFERED_APPOINTMENT_DATE_TIME", _("Offered Appointment Date / Time")
    BOOKED_APPOINTMENT = "BOOKED_APPOINTMENT", _("Booked the Appointment")  # unsure as to whether to keep this since it's a metric elsewhere / separate from agents specifically


class AgentInteractionOvertalkMetricTypes(models.TextChoices):
    NONE = "none"
    INFREQUENT = "infrequent"
    MODERATE = "moderate"
    FREQUENT = "frequent"

