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


class CallOutcomeTypes(models.TextChoices):
    SUCCESS = "success"
    FAILURE = "failure"
    NOT_APPLICABLE = "not_applicable"


class CallOutcomeReasonTypes(models.TextChoices):
    # TODO: Fix incorrect spelling in BQ and ml-stream-pipeline: not_enough_information_possessed_by_patient_or_agent
    NOT_ENOUGH_INFORMATION_POSSESED_BY_PATIENT_OR_AGENT = "not_enough_information_possesed_by_patient_or_agent"
    PROCEDURE_NOT_OFFERED = "procedure_not_offered"
    CALLER_INDIFFERENCE = "caller_indifference"
    INSURANCE = "insurance"
    PRICING = "pricing"
    LOST = "lost"  # TODO: What is lost?
    TREATMENT_NOT_OFFERED = "treatment_not_offered"
    SCHEDULING = "scheduling"  # TODO: Should this be scheduling conflict? What is the context of this?
    DAY_OR_TIME_NOT_AVAILABLE = "day_or_time_not_available"
    TOO_EXPENSIVE = "too_expensive"
    CALL_INTERRUPTED = "call_interrupted"
    INSURANCE_NOT_TAKEN = "insurance_not_taken"
    OTHERS = "others"  # create/refactor as noneoftheabove once we re-do the model and/or frontend
    NOT_APPLICABLE = "not_applicable"


# TODO: Revisit and redo
class PopularProceduresMentioned(models.TextChoices):
    EXAM = "exam"
    RESCHEDULE = "reschedule"
    # TODO: appointment_confirm - matching BQ and ml-stream-pipeline for now
    CONFIRM_APPOINTMENT = "confirm_appointment"
    PRICING = "pricing"
    BILLING = "billing"
    OTHERS = "others"  # TODO: create/refactor as noneoftheabove once we re-do the model and/or frontend
