from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import AuditTrailDateTimeOnlyModel
from core.models import Patient as PeerlogicPatient


class APIRequest(AuditTrailDateTimeOnlyModel):
    """
    Capture all details about a request made to NexHealth and (if applicable) the response received
    """

    class Status(models.TextChoices):
        created = "CREATED"
        error = "ERROR"
        completed = "COMPLETED"

    id = ShortUUIDField(primary_key=True)

    # These come directly from the NexHealthAPIClient
    client_nh_location_id = models.PositiveIntegerField(null=True, db_index=True)
    client_nh_institution_id = models.PositiveIntegerField(null=True, db_index=True)

    # These are mandatory fields set on creation
    request_body = models.TextField(blank=True)
    request_headers = models.JSONField(null=True)
    request_method = models.TextField(blank=False, db_index=True)
    request_path = models.TextField(blank=True, db_index=True)
    request_query_parameters = models.JSONField(null=True)  # Array of tuples
    request_url = models.TextField(blank=False, db_index=True)
    request_nh_id = models.PositiveIntegerField(null=True, db_index=True)
    request_nh_location_id = models.PositiveIntegerField(null=True)
    request_nh_resource = models.CharField(max_length=128, null=True, db_index=True)
    request_nh_subdomain = models.CharField(max_length=128, null=True, db_index=True)
    request_status = models.CharField(max_length=16, blank=False, null=False, choices=Status.choices, db_index=True)

    response_body = models.TextField(null=True)
    response_headers = models.JSONField(null=True)
    response_nh_code = models.BooleanField(null=True)
    response_nh_count = models.PositiveIntegerField(null=True)
    response_nh_data = models.JSONField(null=True)
    response_nh_description = models.JSONField(null=True)  # Array of strings
    response_status = models.PositiveSmallIntegerField(null=True, db_index=True)
    response_time_sec = models.FloatField(null=True)

    # Errors:
    # request_error_details will only be filled when we encounter an error making a request
    #   A 400 response, for example, will NOT result in a request_error_details
    #   Things that might fill in here: timeout/egress issue, SSL issue, certain 5XX cases
    request_error_details = models.TextField(null=True, blank=True)
    # response_nh_error will contain details for validation error sorts of things
    response_nh_error = models.JSONField(null=True)  # Array of strings


class Institution(AuditTrailDateTimeOnlyModel):
    """
    Similar to an "Organization" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/institutions-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_id = models.PositiveIntegerField(unique=True)
    nh_subdomain = models.CharField(max_length=128, unique=True)

    peerlogic_organization = models.ForeignKey(to="core.Organization", on_delete=models.SET_NULL, null=True, related_name="nexhealth_institutions")
    peerlogic_practice = models.ForeignKey(to="core.Practice", on_delete=models.SET_NULL, null=True, related_name="nexhealth_institutions")

    appointment_types_location_scoped = models.BooleanField(null=True)
    country_code = models.CharField(max_length=3)
    emrs = ArrayField(models.CharField(max_length=128), default=list)
    is_appt_categories_location_specific = models.BooleanField(null=True)
    is_sync_notifications = models.BooleanField(null=True)
    name = models.CharField(max_length=255, db_index=True)
    notify_insert_fails = models.BooleanField(null=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)
    synced_patients_to_peerlogic_at = models.DateTimeField(null=True)  # This is the most recent time that we synced to core.Patient records


class Location(AuditTrailDateTimeOnlyModel):
    """
    Similar to a "Practice" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/locations-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_created_at = models.DateTimeField()
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_inactive = models.BooleanField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_updated_at = models.DateTimeField(null=True)
    updated_from_nexhealth_at = models.DateTimeField(null=True)  # This is the most recent time Peerlogic fetched updates for the location
    synced_appointments_to_peerlogic_at = models.DateTimeField(null=True)  # This is the most recent time that we synced to core.Appointment records
    is_initialized = models.BooleanField(default=False)

    peerlogic_practice = models.ForeignKey(to="core.Practice", on_delete=models.SET_NULL, null=True, related_name="nexhealth_locations")
    nh_institution = models.ForeignKey(to=Institution, to_field="nh_id", on_delete=models.CASCADE, related_name="locations")  # type: ignore

    city = models.CharField(max_length=255, null=True)
    email = models.EmailField(null=True)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    insert_appt_client = models.BooleanField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    map_by_operatory = models.BooleanField(null=True)
    name = models.CharField(max_length=255, db_index=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)
    set_availability_by_operatory = models.BooleanField(null=True)
    state = models.CharField(max_length=64, null=True)
    street_address = models.CharField(max_length=255, null=True)
    street_address_2 = models.CharField(max_length=255, null=True)
    tz = models.CharField(max_length=128, null=True)
    zip_code = models.CharField(max_length=12, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nh_id", "nh_institution_id"], name="nh_unique_location_with_institution")]


class Provider(AuditTrailDateTimeOnlyModel):
    """
    Represents an employee who can provide care at a "Location"

    NexHealth Reference: https://docs.nexhealth.com/reference/providers-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_created_at = models.DateTimeField()
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_inactive = models.BooleanField(db_index=True)
    nh_institution_id = models.PositiveIntegerField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_updated_at = models.DateTimeField(null=True)

    availabilities = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/availabilities-1
    bio = models.JSONField(null=True)
    phone_number_best = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number_mobile = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number_home = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number_work = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    display_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    middle_name = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    npi = models.CharField(max_length=128, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nh_id", "nh_institution_id"], name="nh_unique_provider_with_institution")]


class LocationProvider(models.Model):
    """
    Links Location to Provider
    """

    nh_location_id = models.PositiveIntegerField(db_index=True)
    nh_provider_id = models.PositiveIntegerField(db_index=True)
    nh_institution_id = models.PositiveIntegerField(db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nh_location_id", "nh_provider_id", "nh_institution_id"], name="nh_unique_provider_with_location")]


class Patient(AuditTrailDateTimeOnlyModel):
    """
    Similar to a "Patient" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/patients-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_created_at = models.DateTimeField()
    nh_guarantor_id = models.PositiveIntegerField(db_index=True, null=True)
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_inactive = models.BooleanField(db_index=True)
    nh_institution_id = models.PositiveIntegerField(db_index=True)
    nh_last_sync_time = models.DateTimeField(null=True)
    nh_updated_at = models.DateTimeField(null=True)

    adjustments = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/adjustments
    balance_amount = models.CharField(max_length=32, null=True, blank=False)
    balance_currency = models.CharField(max_length=3, null=True, blank=False)
    bio = models.JSONField(null=True)
    date_of_birth = models.DateField(null=True)
    email = models.EmailField(null=True)
    charges = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/getcharges
    first_name = models.CharField(max_length=255, null=True, blank=True)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    middle_name = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    payments = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/getpayments
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number_mobile = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number_home = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    phone_number_work = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON

    unsubscribe_sms = models.BooleanField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nh_id", "nh_institution_id"], name="nh_unique_patient_with_institution")]

    @property
    def peerlogic_patients(self) -> "models.query.QuerySet[PeerlogicPatient]":
        return PeerlogicPatient.objects.filter(id__in=NexHealthPatientLink.objects.filter(nh_institution_id=self.nh_institution_id, nh_patient_id=self.nh_id))


class NexHealthPatientLink(models.Model):
    """
    Links NexHealth Integration Patient to Peerlogic Patient
    """

    nh_institution_id = models.PositiveIntegerField(db_index=True, null=False)
    nh_patient_id = models.PositiveIntegerField(db_index=True, null=False)
    peerlogic_patient = models.ForeignKey(to="core.Patient", on_delete=models.CASCADE, related_name="nexhealth_patient")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nh_institution_id", "nh_patient_id", "peerlogic_patient_id"], name="unique_nexhealth_patient_with_peerlogic_patient"
            )
        ]


class Procedure(AuditTrailDateTimeOnlyModel):
    """
    NexHealth Reference: https://docs.nexhealth.com/reference/procedures
    """

    id = ShortUUIDField(primary_key=True)

    nh_appointment_id = models.PositiveIntegerField(db_index=True)
    nh_id = models.PositiveIntegerField(db_index=True)
    nh_patient_id = models.PositiveIntegerField(db_index=True)
    nh_provider_id = models.PositiveIntegerField(db_index=True)

    nh_institution_id = models.PositiveIntegerField(db_index=True)

    body_site = models.JSONField(null=True)  # e.g. {"tooth": "14", "surface": "MOD"}
    code = models.CharField(max_length=128, db_index=True)
    end_date = models.DateField(null=True)
    fee_amount = models.CharField(max_length=32, null=True, blank=False)
    fee_currency = models.CharField(max_length=3, null=False, blank=False, default="USD")
    name = models.CharField(max_length=255, db_index=True)
    start_date = models.DateField(null=True)

    status = models.CharField(max_length=32)  # treatment_planned/planned, scheduled, completed, inactive, referred

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nh_id", "nh_appointment_id", "nh_institution_id"], name="nh_unique_procedure_with_institution_and_appointment")
        ]


class Appointment(AuditTrailDateTimeOnlyModel):
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
    nh_institution_id = models.PositiveIntegerField(db_index=True)
    nh_deleted = models.BooleanField(db_index=True)

    cancelled = models.BooleanField(null=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True)
    checked_out = models.BooleanField(null=True)
    checked_out_at = models.DateTimeField(null=True)
    checkin_at = models.DateTimeField(null=True)
    confirmed = models.BooleanField(null=True)
    confirmed_at = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    is_guardian = models.BooleanField(null=True)
    is_new_clients_patient = models.BooleanField(null=True)
    is_past_patient = models.BooleanField(null=True, db_index=True)
    misc = models.JSONField(null=True)  # e.g. {"is_booked_on_nexhealth": true}
    note = models.TextField(null=True, blank=True)
    patient_confirmed = models.BooleanField(null=True)
    patient_confirmed_at = models.DateTimeField(null=True)
    patient_missed = models.BooleanField(null=True)
    provider_name = models.CharField(max_length=255, null=True)
    referrer = models.CharField(max_length=255, null=True)
    sooner_if_possible = models.BooleanField(null=True)
    start_time = models.DateTimeField(null=True, db_index=True)
    timezone_offset = models.TextField(max_length=128, null=True, blank=True)
    unavailable = models.BooleanField(null=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nh_id", "nh_location_id", "nh_institution_id"], name="nh_unique_appointment_with_institution_and_location")
        ]


class NexHealthAppointmentLink(models.Model):
    """
    Links NexHealth Integration Appointment to Peerlogic Appointment
    """

    nh_institution_id = models.PositiveIntegerField(db_index=True, null=False)
    nh_appointment_id = models.PositiveIntegerField(db_index=True, null=False)
    peerlogic_appointment = models.ForeignKey(to="core.Appointment", on_delete=models.CASCADE, related_name="nexhealth_appointment")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nh_institution_id", "nh_appointment_id", "peerlogic_appointment_id"], name="unique_nexhealth_appointment_with_peerlogic_appointment"
            )
        ]


class InsurancePlan(AuditTrailDateTimeOnlyModel):
    """
    NexHealth Reference: https://docs.nexhealth.com/reference/insurance-plans
    """

    nh_id = models.PositiveIntegerField(unique=True)
    nh_institution_id = models.PositiveIntegerField(db_index=True)

    country_code = models.CharField(max_length=3)
    state = models.CharField(max_length=64, null=True)
    address = models.CharField(max_length=255, null=True)
    address2 = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    zip_code = models.CharField(max_length=12, null=True)
    name = models.CharField(max_length=255, null=True)
    payer_id = models.CharField(max_length=64, null=True)
    group_num = models.CharField(max_length=64, null=True)
    employer_name = models.CharField(max_length=255, null=True)
    # Note: No foreign_id_type on this one!
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nh_id", "nh_institution_id"], name="nh_unique_insurance_plan_with_institution")]


class InsuranceCoverage(AuditTrailDateTimeOnlyModel):
    """
    NexHealth Reference: https://docs.nexhealth.com/reference/getpatientsidinsurancecoverages
    """

    nh_id = models.PositiveIntegerField(db_index=True)
    nh_insurance_plan_id = models.PositiveIntegerField(db_index=True)
    nh_patient_id = models.PositiveIntegerField(db_index=True)
    nh_institution_id = models.PositiveIntegerField(db_index=True)

    effective_date = models.DateField()
    expiration_date = models.DateField()
    priority = models.PositiveSmallIntegerField()
    subscriber_num = models.CharField(max_length=128)
    subscription_relation = models.CharField(max_length=128)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nh_id", "nh_patient_id", "nh_institution_id"], name="nh_unique_insurance_coverage_with_patient_and_institution")
        ]
