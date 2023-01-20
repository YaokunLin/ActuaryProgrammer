from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import AuditTrailDateTimeOnlyModel, AuditTrailModel
from core.models import Organization, Practice


class Procedure(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    procedure_price_average_in_usd = models.DecimalField(max_digits=7, decimal_places=2)
    ada_code = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)


class Patient(AuditTrailModel):
    address_line_1 = models.CharField(blank=True, max_length=255, null=True)
    address_line_2 = models.CharField(blank=True, max_length=255, null=True)
    date_of_birth = models.DateField(null=True)
    email = models.EmailField(null=True)
    id = ShortUUIDField(primary_key=True, editable=False)
    is_active = models.BooleanField(default=True)
    name = models.CharField(blank=True, null=True, max_length=255, db_index=True)
    name_first = models.CharField(blank=True, null=True, max_length=255)
    name_last = models.CharField(blank=True, null=True, max_length=255, db_index=True)
    name_middle = models.CharField(blank=True, null=True, max_length=255)
    phone_fax = PhoneNumberField(blank=True, null=True, default="")
    phone_home = PhoneNumberField(db_index=True, blank=True, null=True)
    phone_mobile = PhoneNumberField(db_index=True, blank=True, null=True)
    phone_number = PhoneNumberField(db_index=True, blank=True, null=True)
    phone_work = PhoneNumberField(db_index=True, blank=True, null=True)
    placeholder = models.CharField(blank=True, max_length=255, null=True)
    pms_created_at = models.DateTimeField(null=True)
    zip_code = models.CharField(max_length=12, blank=True, null=True)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    practices = models.ManyToManyField(to=Practice, through="PracticePatient", related_name="patients")

    class Meta:
        indexes = [
            models.Index(
                models.functions.Upper("name_last"),
                name="patient_name_last_ci",
            ),
        ]


class PracticePatient(models.Model):
    practice = models.ForeignKey(to=Practice, on_delete=models.CASCADE)
    patient = models.ForeignKey(to=Patient, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["practice_id", "patient_id"], name="unique_care_practice_with_patient")]


class Appointment(AuditTrailDateTimeOnlyModel):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        DELETED = "DELETED"

    appointment_end_at = models.DateTimeField(null=False, db_index=True)
    appointment_start_at = models.DateTimeField(null=False, db_index=True)
    confirmed_at = models.DateTimeField(null=True)
    did_patient_miss = models.BooleanField(null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_new_patient = models.BooleanField(null=True, db_index=True)
    note = models.TextField(null=True)
    patient = models.ForeignKey(to=Patient, on_delete=models.CASCADE, related_name="appointments")
    pms_created_at = models.DateTimeField(null=True)
    practice = models.ForeignKey(to=Practice, on_delete=models.CASCADE, related_name="appointments")
    status = models.CharField(choices=Status.choices, max_length=16, blank=False, null=False, default=Status.SCHEDULED)

    # This can either come directly from the PMS or will be a summation of fee amounts from procedures
    approximate_total_currency = models.CharField(max_length=3, null=False, blank=False, default="USD")
    approximate_total_amount = models.DecimalField(max_digits=24, decimal_places=2, default=0.00)

    # Note on procedures:
    #   These are stored denormalized and simplified with 4 fields each, and should be stored in order of "code":
    #     code: The ADA code for the procedure/treatment
    #     name: The name or description for the procedure from the PMS
    #     fee_currency: The ISO 4217 currency code (e.g. "USD")
    #     fee_amount: The approximate cost of the procedure
    procedures = models.JSONField(null=True)
