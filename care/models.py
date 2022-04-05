from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class Procedure(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    procedure_price_average_in_usd = models.DecimalField(max_digits=7, decimal_places=2)
    keyword = models.CharField(max_length=50)
    ada_code = models.CharField(max_length=50)
