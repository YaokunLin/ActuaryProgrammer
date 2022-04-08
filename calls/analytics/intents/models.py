from dataclasses import field
import logging
from core.abstract_models import AuditTrailModel
from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField

# Get an instance of a logger
log = logging.getLogger(__name__)

from calls.analytics.intents.field_choices import CallPurposeTypes, CallOutcomeTypes, CallOutcomeReasonTypes


class CallPurpose(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="Purpose of the call", related_name="call_purposes")
    call_purpose_type = models.CharField(choices=CallPurposeTypes.choices, max_length=50, db_index=True, blank=True)
    raw_call_purpose_model_run_id = models.CharField(max_length=22)
    call_purpose_model_run = models.ForeignKey(
        "ml.MLModelResultHistory",
        on_delete=models.SET_NULL,
        verbose_name="ml model run for this call purpose",
        related_name="resulting_call_purposes",
        null=True,
    )


class CallOutcome(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_outcome_type = models.CharField(choices=CallOutcomeTypes.choices, max_length=50, db_index=True, blank=True)
    call_purpose = models.ForeignKey(
        CallPurpose, on_delete=models.SET_NULL, verbose_name="The source purpose for this outcome", related_name="outcome_results", null=True
    )
    raw_call_outcome_model_run_id = models.CharField(max_length=22)
    call_outcome_model_run = models.ForeignKey(
        "ml.MLModelResultHistory",
        on_delete=models.SET_NULL,
        verbose_name="ml model run for this call outcome",
        related_name="resulting_call_outcomes",
        null=True,
    )


class CallOutcomeReason(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_outcome = models.ForeignKey(
        CallOutcome, on_delete=models.SET_NULL, verbose_name="The source outcome", related_name="outcome_reason_results", null=True
    )
    call_outcome_reason_type = models.CharField(choices=CallOutcomeReasonTypes.choices, max_length=75, db_index=True, blank=True)
    raw_call_outcome_reason_model_run_id = models.CharField(max_length=22)
    call_outcome_reason_model_run = models.ForeignKey(
        "ml.MLModelResultHistory",
        on_delete=models.SET_NULL,
        verbose_name="ml model run for this call outcome reason",
        related_name="resulting_call_outcome_reasons",
        null=True,
    )


class CallCompanyDiscussed(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="company discussed during a call", related_name="discussed_companies")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table


class CallInsuranceDiscussed(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="insurance discussed during a call", related_name="discussed_insurances")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table



class CallProcedureDiscussed(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="procedure discussed during a call", related_name="discussed_procedures")
    keyword = models.CharField(
        max_length=50, db_index=True, blank=True
    )  # not a formal ForeignKey but will be referenced by ProcedureKeyword, kept as-is so we don't have to have mappings to still extract entities


class ProcedureKeyword(AuditTrailModel):
    procedure = models.ForeignKey(
        "care.Procedure", on_delete=models.SET_NULL, verbose_name="procedures associated with a keyword", related_name="keywords", null=True
    )
    keyword = models.CharField(max_length=50, db_index=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["procedure", "keyword"], name="unique keyword mapping")]


class CallProductDiscussed(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="product discussed during a call", related_name="discussed_products")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table


class CallSymptomDiscussed(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="symptom discussed during a call", related_name="discussed_symptoms")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table
