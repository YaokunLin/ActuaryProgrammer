from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentInteractionGroupType(models.TextChoices):
    INTRO = "introduction"
    SURVEY = "survey"
    SELLING = "selling"
    RAPPORT = "rapport"
    CONVERT = "convert"


class AgentInteractionMetricTypes(models.TextChoices):
    # Intro
    GREETING = "greeting", _("Clear Well Spoken Greeting")
    ANNOUNCED_NAME = "announced_name", _("Announced Name")
    OFFERED_ASSISTANCE = "offered_assistance", _("Offered Assistance")
    STATED_BUSINESS_NAME = "stated_business_name", _("Stated Business Name")
    
    # Survey
    ASKED_PATIENT_NAME = "asked_patient_name", _("Asked for the Patient's Name")
    ASKED_PATIENT_CONTACT_INFO = "asked_patient_contact_info", _("Asked for the Patient's Contact Information")
    ASKED_PATIENT_PURPOSE = "asked_patient_purpose", _("Asked for the Patient's Purpose")
    ASKED_REFERRING_SOURCE = "asked_referring_source", _("Asked About Referring Source")

    # Selling
    MENTIONED_PROCEDURE = "mentioned_procedure", _("Mentioned Procedure Information")
    MENTIONED_INSURANCE_COVERAGE = "mentioned_insurance_coverage", _("Mentioned Insurance Coverage")
    MENTIONED_FINANCING = "mentioned_financing", _("Mentioned Financing / Discount Club / Payment Plans")
    OFFERED_FREE_CONSULTATION = "offered_free_consultation", _("Offered a Free Consultation")
    
    # Rapport
    AGENT_OVERTALK = "agent_overtalk", _("Listened Enough (Limited Overtalk)")
    HOLD_TIME = "hold_time", _("Acceptable Hold Time Length")
    ASKED_ABOUT_DISCOMFORT = "asked_about_discomfort", _("Asked About Discomfort")
    MENTIONED_PRICING = "mentioned_pricing", _("Mentioned Pricing")
    
    # Convert
    OFFERED_APPOINTMENT_DATE_TIME = "offered_appointment_date_time", _("Offered Appointment Date / Time")
    BOOKED_APPOINTMENT = "booked_appointment", _("Booked the Appointment")  # TODO evaluate whether to keep this since it's a metric elsewhere / separate from agents specifically

    # Outbound
    ASKED_INSURANCE = "asked_insurance", _("Asked about / verified insurance")
    ASKED_BILLS = "asked_bills", _("Asked about outstanding bills / balances")
    CALL_LENGTH = "call_length", _("Off the phone quickly")
    ASKED_APPOINTMENT = "asked_appointment", _("Asked about appointment")
    CONFIRM_APPOINTMENT = "confirm_appointment", _("Confirmed / retained appointment")


class AgentInteractionOvertalkMetricTypes(models.TextChoices):
    NONE = "none"
    INFREQUENT = "infrequent"
    MODERATE = "moderate"
    FREQUENT = "frequent"
