from django.db import models

from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class NetsapiensCdrsExtract(AuditTrailModel):
    netsapiens_callid = models.CharField(primary_key=True, max_length=127)
    peerlogic_call_id = models.CharField(blank=True, default="", max_length=22, db_index=True)
    netsapiens_cdrs_extract = models.JSONField(default=dict, help_text="CDRs")


class VeloxPatientExtract(AuditTrailModel):
    velox_id = models.IntegerField(primary_key=True)
    peerlogic_patient_id = models.CharField(blank=True, default="", max_length=22, db_index=True)
    velox_patient_extract_data = models.JSONField(default=dict)
