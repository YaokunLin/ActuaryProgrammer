import logging
from core.abstract_models import AuditTrailModel
from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField

from ml.field_choices import ClassificationDomain

# Get an instance of a logger
log = logging.getLogger(__name__)


class MLModel(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    classification_domain = models.CharField(choices=ClassificationDomain.choices, max_length=100, db_index=True)
    model_version = models.CharField(max_length=64)  # https://github.com/semver/semver/issues/364
    hyper_parameters = models.JSONField(null=True)
    vertex_deployed_model_id = models.CharField(max_length=20, null=True)


class MLModelResultHistory(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    classification_domain = models.CharField(choices=ClassificationDomain.choices, max_length=100, db_index=True)
    call = models.ForeignKey("calls.Call", on_delete=models.CASCADE, verbose_name="model results from the call", related_name="call_model_results")
    model = models.ForeignKey(MLModel, on_delete=models.SET_NULL, null=True, verbose_name="model results from the model runs", related_name="model_results")
    run_id = models.CharField(max_length=22)
    label = models.CharField(max_length=150)
    score = models.FloatField(null=True)
