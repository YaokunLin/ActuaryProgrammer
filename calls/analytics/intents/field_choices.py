from django.db import models
from django.utils.translation import gettext_lazy as _


class CallPurposeTypes(models.TextChoices):
    # TODO: appointment_new - matching BQ and ml-stream-pipeline for now
    NEW_APPOINTMENT = "new_appointment"
    # TODO: appointment_reschedule - matching BQ and ml-stream-pipeline for now
    RESCHEDULE = "reschedule"
    # TODO: appointment_confirm - matching BQ and ml-stream-pipeline for now
    CONFIRM_APPOINTMENT = "confirm_appointment"
    PRICING = "pricing"
    BILLING = "billing"
    OTHERS = "others"  # TODO: create/refactor as noneoftheabove once we re-do the model and/or frontend

    # INSURANCE RELATED
    INSURANCE_AUTHORIZATION = "insurance_authorization"  # authorize a patient to be seen or a procedure to be performed
    INSURANCE_VERIFICATION = "insurance_verification"  # eligibility verification
    INSURANCE_CLAIM = "insurance_claim"  # anything involving claim


class CallOutcomeTypes(models.TextChoices):
    SUCCESS = "success"
    FAILURE = "failure"
    NOT_APPLICABLE = "not_applicable"


class CallOutcomeReasonTypes(models.TextChoices):
    # TODO: Fix incorrect spelling in BQ and ml-stream-pipeline: not_enough_information_possessed_by_patient_or_agent
    NOT_ENOUGH_INFORMATION_POSSESED_BY_PATIENT_OR_AGENT = "not_enough_information_possesed_by_patient_or_agent", _(
        "Not enough information possessed by patient or agent to resolve"
    )
    PROCEDURE_NOT_OFFERED = "procedure_not_offered", _("Procedure not offered")
    CALLER_INDIFFERENCE = "caller_indifference", _("Caller indifference")
    INSURANCE = "insurance", _("Insurance not taken")
    PRICING = "pricing", _("Pricing")  # TODO: is this different than too expensive
    LOST = "lost", _("Lost")  # TODO: What is lost?
    TREATMENT_NOT_OFFERED = "treatment_not_offered", _("Treatment / procedure not offered")
    SCHEDULING = "scheduling", _("Scheduling conflict")  # TODO: Should this be scheduling conflict? What is the context of this?
    DAY_OR_TIME_NOT_AVAILABLE = "day_or_time_not_available", _("Day or time not availabe to schedule")
    TOO_EXPENSIVE = "too_expensive", _("Too expensive")  # TODO: Is this different than pricing
    CALL_INTERRUPTED = "call_interrupted", _("Call was interrupted in the middle")
    INSURANCE_NOT_TAKEN = "insurance_not_taken", _("Insurance not taken")
    OTHERS = "others", _("Other")  # create/refactor as noneoftheabove once we re-do the model and/or frontend
    NOT_APPLICABLE = "not_applicable", _("Not Applicable")

    # insurance claim denied reason types
    INSURANCE_INCORRECT_DENTAL_CODE = "incorrect_dental_code", _("Incorrect dental code")
    INSURANCE_INCOMPLETE_INFORMATION_ON_CLAIM = "incomplete_information_on_claim", _("Incomplete information on claim")
    INSURANCE_COVERAGE_LIMIT_ANNUAL = "insurance_coverage_limit_annual", _("Insurance coverage annual limit")
    INSURANCE_COVERAGE_LIMIT_LIFETIME = "insurance_coverage_limit_lifetime", _("Insurance coverage lifetime limit")
    INSURANCE_COVERAGE_TIME_LIMIT = "insurance_coverage_time_limit", _("Claim not submitted within plan limit")
    INSURANCE_INCORRECT_BENEFICIARY_INFORMATION = "insurance_incorrect_beneficiary_information", _("Incorrect beneficiary information")
    INSURANCE_COVERAGE_EXPIRED = "insurance_coverage_expired", _("Insurance coverage expired")
    INSURANCE_COORDINATION_OF_BENEFITS = "insurance_coordination_of_benefits", _("Coordination of benefits")
    INSURANCE_PREAUTHORIZATION_NOT_OBTAINED = "insurance_preauthorization_not_obtained", _(
        "Pre-authorization / pre-certification not obtained"
    )  # aka pre-certification, prior-authorizations
    INSURANCE_PROCEDURE_NOT_COVERED = "insurance_procedure_not_covered", _("Procedure not covered")


# TODO: Revisit and redo
class PopularProceduresMentioned(models.TextChoices):
    EXAM = "exam"
    RESCHEDULE = "reschedule"
    # TODO: appointment_confirm - matching BQ and ml-stream-pipeline for now
    CONFIRM_APPOINTMENT = "confirm_appointment"
    PRICING = "pricing"
    BILLING = "billing"
    OTHERS = "others"  # TODO: create/refactor as noneoftheabove once we re-do the model and/or frontend
