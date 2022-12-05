from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django_extensions.db.fields import ShortUUIDField
from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import AuditTrailModel


class APIRequest(AuditTrailModel):
    """
    Capture all details about a request made to NexHealth and (if applicable) the response received
    """

    id = ShortUUIDField(primary_key=True)

    request_body = models.TextField(blank=True)
    request_headers = models.JSONField(null=True)
    request_method = models.TextField(blank=False, db_index=True)
    request_path = models.TextField(blank=True, db_index=True)
    request_query_parameters = models.JSONField(null=True)  # Array of objects with key, value
    request_url = models.TextField(blank=False, db_index=True)

    response_body = models.TextField(null=True)
    response_headers = models.JSONField(null=True)
    response_nh_code = models.NullBooleanField()
    response_nh_count = models.PositiveIntegerField(null=True)
    response_nh_data = JSONField(null=True)
    response_nh_description = JSONField(null=True)
    response_nh_error = JSONField(null=True)
    response_status = models.PositiveSmallIntegerField(null=True, db_index=True)
    response_time_sec = models.PositiveIntegerField(null=True)


class Institution(AuditTrailModel):
    """
    Typically nalagous to an "Organization" in Peerlogic

    NexHealth Reference: https://docs.nexhealth.com/reference/institutions-1
    """

    id = ShortUUIDField(primary_key=True)

    nh_id = models.PositiveIntegerField(db_index=True)

    peerlogic_organization = models.ForeignKey(to="core.Organization", on_delete=models.SET_NULL, null=True)
    peerlogic_practice = models.ForeignKey(to="core.Practice", on_delete=models.SET_NULL, null=True)

    appointment_types_location_scoped = models.NullBooleanField()
    country_code = models.CharField(max_length=3)
    emrs = ArrayField(models.CharField(max_length=128), default=list)
    is_appt_categories_location_specific = models.NullBooleanField()
    is_sync_notifications = models.NullBooleanField()
    name = models.CharField(max_length=255, db_index=True)
    notify_insert_fails = models.NullBooleanField()
    phone_extension = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)
    subdomain = models.CharField(max_length=128, db_index=True)


class Location(AuditTrailModel):
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

    institution = models.ForeignKey(to=Institution, on_delete=models.SET_NULL, null=True)
    peerlogic_practice = models.ForeignKey(to="core.Practice", on_delete=models.SET_NULL, null=True)
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
    insert_appt_client = models.NullBooleanField()
    latitude = models.PositiveSmallIntegerField(null=True)
    longitude = models.PositiveSmallIntegerField(null=True)
    map_by_operatory = models.NullBooleanField()
    name = models.CharField(max_length=255, db_index=True)
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)
    set_availability_by_operatory = models.NullBooleanField()
    state = models.CharField(max_length=64, null=True)
    street_address = models.CharField(max_length=255, null=True)
    street_address_2 = models.CharField(max_length=255, null=True)
    tz = models.CharField(max_length=128, null=True)
    zip_code = models.CharField(max_length=12, null=True)


class Provider(AuditTrailModel):
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

    institution = models.ForeignKey(to=Institution, on_delete=models.SET_NULL, null=True)

    availabilities = models.JSONField(null=True)  # https://docs.nexhealth.com/reference/availabilities-1
    bio = JSONField(null=True)
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


class LocationProvider(AuditTrailModel):
    """
    Links Location to Provider
    """

    id = ShortUUIDField(primary_key=True)

    nh_location_id = models.PositiveIntegerField()
    nh_provider_id = models.PositiveIntegerField()

    location = models.ForeignKey(to=Location, on_delete=models.SET_NULL, null=True)
    provider = models.ForeignKey(to=Provider, on_delete=models.SET_NULL, null=True)

    is_bookable = models.NullBooleanField()


class Patient(AuditTrailModel):
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
    institution = models.ForeignKey(to=Institution, on_delete=models.SET_NULL, null=True)
    providers = models.ManyToManyField(
        to=Provider,
        through="nexhealth_integration.Appointment",
        through_fields=(
            "patient",
            "provider",
        ),
        related_name="patients",
    )

    adjustments = JSONField(null=True)  # https://docs.nexhealth.com/reference/adjustments
    balance_amount = models.CharField(max_length=32, null=True, blank=False)
    balance_currency = models.CharField(max_length=3, null=True, blank=False)
    bio = JSONField(null=True)
    charges = JSONField(null=True)  # https://docs.nexhealth.com/reference/getcharges
    date_of_birth = models.DateField(null=True)  # From bio JSON
    first_name = models.CharField(max_length=255)
    foreign_id = models.CharField(max_length=255, null=True, db_index=True)
    foreign_id_type = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255, db_index=True)
    payments = JSONField(null=True)  # https://docs.nexhealth.com/reference/getpayments
    phone_number = PhoneNumberField(null=True, blank=True, db_index=True)  # From bio JSON
    unsubscribe_sms = models.NullBooleanField()


class Procedure(AuditTrailModel):
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

    body_site = JSONField(null=True)  # e.g. {"tooth": "14", "surface": "MOD"}
    code = models.CharField(max_length=128, db_index=True)
    end_date = models.DateField(null=True)
    fee_amount = models.CharField(max_length=32, null=True, blank=False)
    fee_currency = models.CharField(max_length=3, null=True, blank=False)
    name = models.CharField(max_length=255, db_index=True)
    start_date = models.DateField(null=True)

    status = models.CharField(max_length=32)  # treatment_planned/planned, scheduled, completed, inactive, referred


class Appointment(AuditTrailModel):
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


class InsurancePlan(AuditTrailModel):
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


class InsuranceCoverage(AuditTrailModel):
    """
    NexHealth Reference: https://docs.nexhealth.com/reference/getpatientsidinsurancecoverages
    """

    nh_id = models.PositiveIntegerField(db_index=True)
    nh_insurance_plan_id = models.PositiveIntegerField(db_index=True)
    nh_patient_id = models.PositiveIntegerField(db_index=True)

    insurance_plan = models.ForeignKey(to=InsurancePlan, on_delete=models.SET_NULL, null=True)
    patient = models.ForeignKey(to=Patient, on_delete=models.SET_NULL, null=True)

    effective_date = models.DateField()
    expiration_date = models.DateField()
    priority = models.PositiveSmallIntegerField()
    subscriber_num = models.CharField(max_length=128)
    subscription_relation = models.CharField(max_length=128)
