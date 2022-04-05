import logging
from core.abstract_models import AuditTrailModel
from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField

from ml.field_choices import ModelTypes

# Get an instance of a logger
log = logging.getLogger(__name__)


class MLModel(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    model_type = models.CharField(choices=ModelTypes.choices, max_length=100, db_index=True, blank=True)
    model_version = models.CharField(max_length=64)  # https://github.com/semver/semver/issues/364
    # TODO: hyper_parameters


class MLModelResultHistory(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("calls.Call", on_delete=models.CASCADE, verbose_name="model results from the call", related_name="call_model_results")
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, verbose_name="model results from the model runs", related_name="model_results")
    run_id = models.CharField(max_length=22)
    label = models.CharField(max_length=150)
    score = models.FloatField()
    # TODO: threshold
