from django.db import models

from django_extensions.db.fields import ShortUUIDField


class VeloxExtractData(models.Model):
    def velox_extract_data_default():
        return {}

    velox_id = models.IntegerField(primary_key=True) # Velox id, not peerlogic-api id
    peerlogic_id = ShortUUIDField( editable=False)
    deleted = models.BooleanField()
    pms_id = models.IntegerField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    guarantor_id = models.CharField(max_length=255)
    dob = models.DateTimeField()
    mobile_phone = models.IntegerField()
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255)
    zip = models.IntegerField()
    email = models.EmailField(max_length=254)
    status = models.IntegerField()
    velox_extract_data = models.JSONField(default=velox_extract_data_default)
