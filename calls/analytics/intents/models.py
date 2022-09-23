import logging

from django.db import models
from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel

# Get an instance of a logger
log = logging.getLogger(__name__)

from calls.analytics.intents.field_choices import (
    CallOutcomeReasonTypes,
    CallOutcomeTypes,
    CallPurposeTypes,
)


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
        CallPurpose, unique=True, on_delete=models.SET_NULL, verbose_name="The source purpose for this outcome", related_name="outcome_results", null=True
    )  # TODO: make a history table to capture older values / older runs
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


class CallMentionedCompany(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="company mentioned during a call", related_name="mentioned_companies")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table


class CallMentionedInsurance(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="insurance mentioned during a call", related_name="mentioned_insurances")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table


class CallMentionedProcedure(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="procedure mentioned during a call", related_name="mentioned_procedures")
    keyword = models.CharField(
        max_length=50, db_index=True, blank=True
    )  # not a formal ForeignKey but will be referenced by ProcedureKeyword. We need to extract and store entities from a call even if we don't have an entry in Procedures


class ProcedureKeyword(AuditTrailModel):
    # TODO: fix related name
    procedure = models.ForeignKey(
        "care.Procedure", on_delete=models.SET_NULL, verbose_name="procedures associated with a keyword", related_name="keywords", null=True
    )
    keyword = models.CharField(max_length=50, db_index=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["procedure", "keyword"], name="unique keyword mapping")]


class CallMentionedProduct(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="product mentioned during a call", related_name="mentioned_products")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table


class CallMentionedSymptom(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="symptom mentioned during a call", related_name="mentioned_symptoms")
    keyword = models.CharField(max_length=50, db_index=True, blank=True)  # not a formal ForeignKey but will eventually require validation from another table
