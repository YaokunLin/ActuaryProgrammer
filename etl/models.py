from django.db import models

from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class VeloxPatientExtract(AuditTrailModel):
    velox_id = models.IntegerField(primary_key=True)  # Velox id, not peerlogic-api id
    peerlogic_patient_id = ShortUUIDField(blank=True)
    velox_patient_extract_data = models.JSONField(default=dict)
