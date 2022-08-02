from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentInteractionMetricTypes(models.TextChoices):
    PAYMENT_METHOD = "payment_method"
    PATIENT_DEMOGRAPHICS = "patient_demographics"

    GREETING = "Clear Well Spoken Greeting"
    ANNOUNCED_NAME = "Announced Name"
    OFFERED_ASSISTANCE = "Offered Assistance"
    STATED_BUSINESS_NAME = "Stated Business Name"
    
    COLLECTED_PATIENT_NAME = "Asked for the Patient's Name"
    COLLECTED_PATIENT_CONTACT_INFO = "Asked for the Patient's Contact Information"
    COLLECTED_PAITENT_PURPOSE = "Asked for the Patient's Purpose"
    ASKED_REFERRING_SOURCE = "Asked About Referring Source"

    DISCUSSED_PROCEDURE = "Discussed Procedure Information"
    DISCUSSED_INSURANCE_COVERAGE = "Discussed Insurance Coverage"
    MENTIONED_FINANCING = "Mentioned Financing / Discount Club / Payment Plans"
    OFFERED_FREE_CONSULTATION = "Offered a Free Consultation"
    
    AGENT_OVERTALK = "Listened Enough (Limited Overtalk)"
    HOLD_TIME = "Acceptable Hold Time Length"
    ASKED_ABOUT_DISCOMFORT = "Asked About Discomfort"
    MENTIONED_PRICING = "Mentioned Pricing"
    
    OFFERED_APPOINTMENT_DATE_TIME =  "Offered Appointment Date / Time"
    BOOKED_APPOINTMENT = "Booked the Appointment"  # unsure as to whether to keep this since it's a duplicate


class AgentInteractionOvertalkMetricTypes(models.TextChoices):
    NONE = "none"
    INFREQUENT = "infrequent"
    MODERATE = "moderate"
    FREQUENT = "frequent"

