from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentInteractionGroupType(models.TextChoices):
    INTRO = "introduction"
    SURVEY = "survey"
    SELLING = "selling"
    RAPPORT = "rapport"
    CONVERT = "convert"
    PROVIDE = "provide"


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

    # Outbound - Rapport
    ASKED_INSURANCE = "asked_insurance", _("Asked about / verified insurance")
    ASKED_BILLS = "asked_bills", _("Asked about outstanding bills / balances")
    CALL_LENGTH = "call_length", _("Off the phone quickly")

    # Outbound - Selling
    ASKED_APPOINTMENT = "asked_appointment", _("Asked about appointment")
    CONFIRM_APPOINTMENT = "confirm_appointment", _("Confirmed / retained appointment")

    # Outbound - Insurance - Provide
    PROVIDED_PATIENT_NAME = "provided_patient_name", _("Provided patient name")
    PROVIDED_PATIENT_INSURANCE_IDS = "provided_patient_insurance_ids", _("Provided patient insurance ids ")
    PROVIDED_PATIENT_DATE_OF_BIRTH = "provided_patient_date_of_birth", _("Provided patient date of birth")
    PROVIDED_SOCIAL_SECURITY_NUMBER = "provided_social_security_number", _("Provided Social Security Number")

    # Outbound - Insurance - Survey
    ASKED_POLICY_ACTIVE = "asked_policy_active", _("Asked policy active / effective date")
    ASKED_POLICY_EXPIRATION_DATE = "asked_policy_expiration_date", _("Asked policy expiration date")
    ASKED_AUTHORIZATION_REQUIREMENTS = "asked_authorization_requirements", _("Asked authorization requirements")



class AgentInteractionOvertalkMetricTypes(models.TextChoices):
    NONE = "none"
    INFREQUENT = "infrequent"
    MODERATE = "moderate"
    FREQUENT = "frequent"
