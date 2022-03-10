from django.db import models

from core.abstract_models import AuditTrailModel


class VeloxPatientExtract(AuditTrailModel):
    velox_id = models.IntegerField(primary_key=True)
    peerlogic_patient_id = models.CharField(blank=True, default="", max_length=22, db_index=True)
    velox_patient_extract_data = models.JSONField(default=dict)
