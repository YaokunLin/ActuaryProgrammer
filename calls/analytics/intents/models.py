import logging
from core.abstract_models import AuditTrailModel
from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField

# Get an instance of a logger
log = logging.getLogger(__name__)

from calls.analytics.intents.field_choices import CallPurposeTypes, CallOutcomeTypes, CallOutcomeReasonTypes


class CallOutcomeReason(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_outcome_reason_type = models.CharField(choices=CallOutcomeReasonTypes.choices, max_length=75, db_index=True, blank=True)


class CallOutcome(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_outcome_type = models.CharField(choices=CallOutcomeTypes.choices, max_length=50, db_index=True, blank=True)
    call_outcome_reason = models.ForeignKey(
        CallOutcomeReason, on_delete=models.SET_NULL, verbose_name="The outcome from the call's purpose", related_name="source_outcomes", null=True
    )


class CallPurpose(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(
        "Call", on_delete=models.CASCADE, verbose_name="Purpose of the call", related_name="purposes"
    )
    call_purpose_type = models.CharField(choices=CallPurposeTypes.choices, max_length=50, db_index=True, blank=True)
    call_outcome = models.ForeignKey(
        CallOutcome, on_delete=models.SET_NULL, verbose_name="The result of the attempted purpose", related_name="source_purposes", null=True
    )
