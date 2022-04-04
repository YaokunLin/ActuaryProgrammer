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
    # TODO: Foreign key of call_purpose_model_run to results history when available


class CallOutcome(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_outcome_type = models.CharField(choices=CallOutcomeTypes.choices, max_length=50, db_index=True, blank=True)
    call_purpose = models.ForeignKey(
        CallPurpose, on_delete=models.SET_NULL, verbose_name="The source purpose for this outcome", related_name="outcome_results", null=True
    )
    raw_call_outcome_model_run_id = models.CharField(max_length=22)
    # TODO: Foreign key of call_outcome_model_run to results history when available


class CallOutcomeReason(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_outcome = models.ForeignKey(
        CallOutcome, on_delete=models.SET_NULL, verbose_name="The source outcome", related_name="outcome_reason_results", null=True
    )
    call_outcome_reason_type = models.CharField(choices=CallOutcomeReasonTypes.choices, max_length=75, db_index=True, blank=True)
    raw_call_outcome_reason_model_run_id = models.CharField(max_length=22)
    # TODO: Foreign key of call_outcome_reason_model_run to results history when available


class CallProcedureDiscussed(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="procedure reference discussed during a call", related_name="procedures_discussed")
    procedure = models.ForeignKey("care.Procedure", on_delete=models.CASCADE, verbose_name="procedure", related_name="calls_in_which_discussed")
