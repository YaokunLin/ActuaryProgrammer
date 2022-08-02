from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentInteractionMetricTypes(models.TextChoices):
    # Intro
    GREETING = "Clear Well Spoken Greeting"
    ANNOUNCED_NAME = "Announced Name"
    OFFERED_ASSISTANCE = "Offered Assistance"
    STATED_BUSINESS_NAME = "Stated Business Name"
    
    # Survey
    COLLECTED_PATIENT_NAME = "Asked for the Patient's Name"
    COLLECTED_PATIENT_CONTACT_INFO = "Asked for the Patient's Contact Information"
    COLLECTED_PATIENT_PURPOSE = "Asked for the Patient's Purpose"
    ASKED_REFERRING_SOURCE = "Asked About Referring Source"

    # Score
    DISCUSSED_PROCEDURE = "Discussed Procedure Information"
    DISCUSSED_INSURANCE_COVERAGE = "Discussed Insurance Coverage"
    DISCUSSED_FINANCING = "Discussed Financing / Discount Club / Payment Plans"
    OFFERED_FREE_CONSULTATION = "Offered a Free Consultation"
    
    # Rapport
    AGENT_OVERTALK = "Listened Enough (Limited Overtalk)"
    HOLD_TIME = "Acceptable Hold Time Length"
    ASKED_ABOUT_DISCOMFORT = "Asked About Discomfort"
    DISCUSSED_PRICING = "Discussed Pricing"
    
    # Convert
    OFFERED_APPOINTMENT_DATE_TIME =  "Offered Appointment Date / Time"
    BOOKED_APPOINTMENT = "Booked the Appointment"  # unsure as to whether to keep this since it's a metric elsewhere / separate from agents specifically


class AgentInteractionGroupType(models.TextChoices):
    INTRO = "Introduction"
    SURVEY = "Survey"
    SCORE = "Score"
    RAPPORT = "Rapport"
    CONVERT = "Convert"


class AgentInteractionOvertalkMetricTypes(models.TextChoices):
    NONE = "none"
    INFREQUENT = "infrequent"
    MODERATE = "moderate"
    FREQUENT = "frequent"

