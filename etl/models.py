from django.db import models

# Create your models here.
class VeloxExtractData(models.Model):
    id = models.IntegerField() # Velox id, not peerlogic-api id
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
    status = models.IntegerField(max_length=255)

