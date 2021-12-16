from django.db import models

# Create your models here.
class VeloxExtractData(models.Model):
    id = models.IntegerField() # Velox id, not peerlogic-api id
    deleted = models.BooleanField()
    pms_id = models.IntegerField()
    first_name = models.CharField()
    last_name = models.CharField()
    guarantor_id = models.CharField()
    dob = models.DateTimeField()
    mobile_phone = models.IntegerField()
    address_line1 = models.CharField()
    address_line2 = models.CharField()
    zip = models.IntegerField()
    email = models.CharField()
    status = models.IntegerField()

