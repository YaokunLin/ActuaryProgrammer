from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import DateTimeOnlyAuditTrailModel


class APIRequest(DateTimeOnlyAuditTrailModel):
    """
    Capture all details about a request made to NexHealth and (if applicable) the response received
    """

    class Status(models.TextChoices):
        created = "CREATED"
        error = "ERROR"
        completed = "COMPLETED"

    id = ShortUUIDField(primary_key=True)

    request_body = models.TextField(blank=True)
    request_headers = models.JSONField(null=True)
    request_method = models.TextField(blank=False, db_index=True)
    request_path = models.TextField(blank=True, db_index=True)
    request_query_parameters = models.JSONField(null=True)  # Array of tuples
    request_url = models.TextField(blank=False, db_index=True)
    request_nh_id = models.PositiveIntegerField(null=True, db_index=True)
    request_nh_location_id = models.PositiveIntegerField(null=True, db_index=True)
    request_nh_resource = models.CharField(max_length=128, null=True, db_index=True)
    request_nh_subdomain = models.CharField(max_length=128, null=True, db_index=True)
    request_status = models.CharField(max_length=16, blank=False, null=False, choices=Status.choices, db_index=True)
    request_error_details = models.TextField(null=True, blank=True)

    response_body = models.TextField(null=True)
    response_headers = models.JSONField(null=True)
    response_nh_code = models.BooleanField(null=True)
    response_nh_count = models.PositiveIntegerField(null=True)
    response_nh_data = models.JSONField(null=True)
    response_nh_description = models.JSONField(null=True)  # Array of strings
    response_nh_error = models.JSONField(null=True)  # Array of strings
    response_status = models.PositiveSmallIntegerField(null=True, db_index=True)
    response_time_sec = models.FloatField(null=True)


class Institution(DateTimeOnlyAuditTrailModel):
    """
    Similar to an "Organization" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/institutions-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_id = models.PositiveIntegerField(db_index=True)

    peerlogic_organization = models.ForeignKey(to="core.Organization", on_delete=models.SET_NULL, null=True, related_name="nexhealth_institutions")
    peerlogic_practice = models.ForeignKey(to="core.Practice", on_delete=models.SET_NULL, null=True, related_name="nexhealth_institutions")

    appointment_types_location_scoped = models.BooleanField(null=True)
    country_code = models.CharField(max_length=3)
    emrs = ArrayField(models.CharField(max_length=128), default=list)
    is_appt_categories_location_specific = models.BooleanField(null=True)
    is_sync_notifications = models.BooleanField(null=True)
    name = models.CharField(max_length=255, db_index=True)
    notify_insert_fails = models.BooleanField(null=True)
    phone_extension = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)
    subdomain = models.CharField(max_length=128, db_index=True)


class Location(DateTimeOnlyAuditTrailModel):
    """
    Similar to a "Practice" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/locations-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_created_at = models.DateTimeField()
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_inactive = models.BooleanField()
    nh_institution_id = models.PositiveIntegerField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_updated_at = models.DateTimeField(null=True)

    institution = models.ForeignKey(to=Institution, on_delete=models.SET_NULL, null=True, related_name="locations")
    peerlogic_practice = models.ForeignKey(to="core.Practice", on_delete=models.SET_NULL, null=True, related_name="nexhealth_locations")
    providers = models.ManyToManyField(
        to="nexhealth_integration.Provider",
        through="nexhealth_integration.LocationProvider",
        through_fields=(
            "location",
            "provider",
        ),
        related_name="locations",
    )
    patients = models.ManyToManyField(
        to="nexhealth_integration.Patient",
        through="nexhealth_integration.Appointment",
        through_fields=(
            "location",
            "patient",
        ),
        related_name="locations",
    )

    city = models.CharField(max_length=255, null=True)
    email = models.EmailField(null=True)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    insert_appt_client = models.BooleanField(null=True)
    latitude = models.PositiveSmallIntegerField(null=True)
    longitude = models.PositiveSmallIntegerField(null=True)
    map_by_operatory = models.BooleanField(null=True)
    name = models.CharField(max_length=255, db_index=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)
    set_availability_by_operatory = models.BooleanField(null=True)
    state = models.CharField(max_length=64, null=True)
    street_address = models.CharField(max_length=255, null=True)
    street_address_2 = models.CharField(max_length=255, null=True)
    tz = models.CharField(max_length=128, null=True)
    zip_code = models.CharField(max_length=12, null=True)


class Provider(DateTimeOnlyAuditTrailModel):
    """
    Represents an employee who can provide care at a "Location"

    NexHealth Reference: https://docs.nexhealth.com/reference/providers-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_created_at = models.DateTimeField()
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_inactive = models.BooleanField()
    nh_institution_id = models.PositiveIntegerField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_updated_at = models.DateTimeField(null=True)

    institution = models.ForeignKey(to=Institution, on_delete=models.SET_NULL, null=True, related_name="providers")

    availabilities = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/availabilities-1
    bio = models.JSONField(null=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    date_of_birth = models.DateField(null=True)  # From bio JSON
    display_name = models.CharField(max_length=255, null=True)
    email = models.EmailField(null=True)
    first_name = models.CharField(max_length=255)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255, db_index=True)
    npi = models.CharField(max_length=128, db_index=True)


class LocationProvider(DateTimeOnlyAuditTrailModel):
    """
    Links Location to Provider
    """

    id = ShortUUIDField(primary_key=True)

    nh_location_id = models.PositiveIntegerField()
    nh_provider_id = models.PositiveIntegerField()

    location = models.ForeignKey(to=Location, on_delete=models.SET_NULL, null=True)
    provider = models.ForeignKey(to=Provider, on_delete=models.SET_NULL, null=True)

    is_bookable = models.BooleanField(null=True)


class Patient(DateTimeOnlyAuditTrailModel):
    """
    Similar to a "Patient" in Peerlogic
    Note: One NexHealth Patient may link to numerous Peerlogic Patients
        This is because in NexHealth, patients are bound to an institution
        and are linked to practices through Appointments.

    NexHealth Reference: https://docs.nexhealth.com/reference/patients-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_created_at = models.DateTimeField()
    nh_guarantor_id = models.PositiveIntegerField(db_index=True)
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_inactive = models.BooleanField()
    nh_institution_id = models.PositiveIntegerField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_updated_at = models.DateTimeField(null=True)

    guarantor = models.ForeignKey(to="nexhealth_integration.Patient", on_delete=models.CASCADE, null=True, related_name="depdendents")
    institution = models.ForeignKey(to=Institution, on_delete=models.SET_NULL, null=True, related_name="patients")
    providers = models.ManyToManyField(
        to=Provider,
        through="nexhealth_integration.Appointment",
        through_fields=(
            "patient",
            "provider",
        ),
        related_name="patients",
    )
    peerlogic_patients = models.ManyToManyField(
        to="core.Patient",
        through="nexhealth_integration.NexHealthPatientLink",
        through_fields=(
            "nh_patient",
            "peerlogic_patient",
        ),
        related_name="nexhealth_patients",
    )

    adjustments = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/adjustments
    balance_amount = models.CharField(max_length=32, null=True, blank=False)
    balance_currency = models.CharField(max_length=3, null=True, blank=False)
    bio = models.JSONField(null=True)
    charges = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/getcharges
    date_of_birth = models.DateField(null=True)  # From bio JSON
    first_name = models.CharField(max_length=255)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255, db_index=True)
    payments = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/getpayments
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    unsubscribe_sms = models.BooleanField(null=True)


class NexHealthPatientLink(models.Model):
    """
    Through-model linking NexHealth Integration Patient to Peerlogic Patient
    """

    nh_patient = models.ForeignKey(to=Patient, on_delete=models.CASCADE)
    peerlogic_patient = models.ForeignKey(to="core.Patient", on_delete=models.CASCADE)


class Procedure(DateTimeOnlyAuditTrailModel):
    """
    Similar to a "Procedure" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/procedures
    """

    id = ShortUUIDField(primary_key=True)

    nh_appointment_id = models.PositiveIntegerField(db_index=True)
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_patient_id = models.PositiveIntegerField(db_index=True)
    nh_provider_id = models.PositiveIntegerField(db_index=True)

    appointment = models.ForeignKey(to="nexhealth_integration.Appointment", on_delete=models.SET_NULL, null=True, related_name="procedures")
    provider = models.ForeignKey(to="nexhealth_integration.Provider", on_delete=models.SET_NULL, null=True, related_name="procedures")
    patient = models.ForeignKey(to="nexhealth_integration.Patient", on_delete=models.SET_NULL, null=True, related_name="procedures")

    body_site = models.JSONField(null=True)  # e.g. {"tooth": "14", "surface": "MOD"}
    code = models.CharField(max_length=128, db_index=True)
    end_date = models.DateField(null=True)
    fee_amount = models.CharField(max_length=32, null=True, blank=False)
    fee_currency = models.CharField(max_length=3, null=True, blank=False)
    name = models.CharField(max_length=255, db_index=True)
    start_date = models.DateField(null=True)

    status = models.CharField(max_length=32)  # treatment_planned/planned, scheduled, completed, inactive, referred


class Appointment(DateTimeOnlyAuditTrailModel):
    """
    Links a Patient, Location, Provider and Procedure

    NexHealth Reference: https://docs.nexhealth.com/reference/appointments-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_appointment_type_id = models.PositiveIntegerField(db_index=True, null=True)
    nh_created_at = models.DateTimeField()
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_location_id = models.PositiveIntegerField(db_index=True)
    nh_operatory_id = models.PositiveIntegerField(db_index=True, null=True)
    nh_patient_id = models.PositiveIntegerField(db_index=True)
    nh_provider_id = models.PositiveIntegerField(db_index=True)
    nh_updated_at = models.DateTimeField(null=True)

    location = models.ForeignKey(to="nexhealth_integration.Location", on_delete=models.SET_NULL, null=True, related_name="appointments")
    patient = models.ForeignKey(to="nexhealth_integration.Patient", on_delete=models.SET_NULL, null=True, related_name="appointments")
    provider = models.ForeignKey(to="nexhealth_integration.Provider", on_delete=models.SET_NULL, null=True, related_name="appointments")

    cancelled = models.BooleanField()
    cancelled_at = models.DateTimeField(null=True)
    checked_out = models.BooleanField()
    checked_out_at = models.DateTimeField(null=True)
    checkin_at = models.DateTimeField(null=True)
    confirmed = models.BooleanField()
    confirmed_at = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    is_guardian = models.BooleanField()
    is_new_clients_patient = models.BooleanField()
    is_past_patient = models.BooleanField()
    misc = models.JSONField(null=True)  # e.g. {"is_booked_on_nexhealth": true}
    nh_deleted = models.BooleanField()
    note = models.TextField(null=True, blank=True)
    patient_confirmed = models.BooleanField()
    patient_confirmed_at = models.DateTimeField(null=True)
    patient_missed = models.BooleanField()
    provider_name = models.CharField(max_length=255, null=True)
    referrer = models.CharField(max_length=255, null=True)
    sooner_if_possible = models.BooleanField()
    start_time = models.DateTimeField(null=True)
    timezone_offset = models.TextField(max_length=128, null=True, blank=True)
    unavailable = models.BooleanField()


class InsurancePlan(DateTimeOnlyAuditTrailModel):
    """
    NexHealth Reference: https://docs.nexhealth.com/reference/insurance-plans
    """

    nh_id = models.PositiveIntegerField(db_index=True)

    country_code = models.CharField(max_length=3)
    state = models.CharField(max_length=64, null=True)
    address = models.CharField(max_length=255, null=True)
    address2 = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    zip_code = models.CharField(max_length=12, null=True)
    name = models.CharField(max_length=255)
    payer_id = models.CharField(max_length=64)
    group_num = models.CharField(max_length=64)
    employer_name = models.CharField(max_length=255)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)


class InsuranceCoverage(DateTimeOnlyAuditTrailModel):
    """
    NexHealth Reference: https://docs.nexhealth.com/reference/getpatientsidinsurancecoverages
    """

    nh_id = models.PositiveIntegerField(db_index=True)
    nh_insurance_plan_id = models.PositiveIntegerField(db_index=True)
    nh_patient_id = models.PositiveIntegerField(db_index=True)

    insurance_plan = models.ForeignKey(to=InsurancePlan, on_delete=models.SET_NULL, null=True, related_name="insurance_coverages")
    patient = models.ForeignKey(to=Patient, on_delete=models.SET_NULL, null=True, related_name="insurance_coverages")

    effective_date = models.DateField()
    expiration_date = models.DateField()
    priority = models.PositiveSmallIntegerField()
    subscriber_num = models.CharField(max_length=128)
    subscription_relation = models.CharField(max_length=128)
