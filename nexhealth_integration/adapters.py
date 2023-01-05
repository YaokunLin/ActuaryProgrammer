from datetime import datetime, timedelta
from logging import getLogger
from typing import Dict, Iterable, Optional, Tuple

from django.db.transaction import atomic
from django.utils import timezone

from core import models as core_models
from nexhealth_integration.models import (
    Appointment,
    Institution,
    InsuranceCoverage,
    InsurancePlan,
    Location,
    LocationProvider,
    NexHealthAppointmentLink,
    NexHealthPatientLink,
    Patient,
    Procedure,
    Provider,
)
from nexhealth_integration.utils import (
    NexHealthLogAdapter,
    get_phone_numbers_from_bio,
    parse_nh_datetime_str,
)

log = NexHealthLogAdapter(getLogger(__name__))


def update_or_create_institution_from_dict(
    data: Dict,
    peerlogic_organization: Optional[core_models.Organization] = None,
    peerlogic_practice: Optional[core_models.Practice] = None,
) -> Tuple[Institution, bool]:
    nh_id = data["id"]
    defaults = {
        "nh_id": nh_id,
        "nh_subdomain": data["subdomain"],
        "appointment_types_location_scoped": data["appointment_types_location_scoped"],
        "country_code": data["country_code"],
        "emrs": data["emrs"],
        "is_appt_categories_location_specific": data["is_appt_categories_location_specific"],
        "is_sync_notifications": data["is_sync_notifications"],
        "name": data["name"],
        "notify_insert_fails": data["notify_insert_fails"],
        "phone_number": data["phone_number"],
    }
    if peerlogic_organization:
        defaults["peerlogic_organization_id"] = peerlogic_organization.id
    if peerlogic_practice:
        defaults["peerlogic_practice_id"] = peerlogic_practice.id

    return Institution.objects.update_or_create(
        nh_id=nh_id,
        defaults=defaults,
    )


def update_or_create_location_from_dict(
    data: Dict,
    peerlogic_practice: Optional[core_models.Practice] = None,
) -> Tuple[Location, bool]:
    nh_id = data["id"]
    nh_institution_id = data["institution_id"]
    defaults = {
        "nh_id": nh_id,
        "nh_institution_id": nh_institution_id,
        "nh_created_at": parse_nh_datetime_str(data["created_at"]),
        "nh_inactive": data["inactive"],
        "nh_last_sync_time": parse_nh_datetime_str(data["last_sync_time"]),
        "nh_updated_at": parse_nh_datetime_str(data["updated_at"]),
        "city": data["city"],
        "email": data["email"],
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "insert_appt_client": data["insert_appt_client"],
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "map_by_operatory": data["map_by_operatory"],
        "name": data["name"],
        "phone_number": data["phone_number"],
        "set_availability_by_operatory": data["set_availability_by_operatory"],
        "state": data["state"],
        "street_address": data["street_address"],
        "street_address_2": data["street_address_2"],
        "tz": data["tz"],
        "zip_code": data["zip_code"],
    }
    if peerlogic_practice:
        defaults["peerlogic_practice_id"] = peerlogic_practice.id

    return Location.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def update_or_create_patient_from_dict(data: Dict, should_create_or_update_related_insurances: bool = False) -> Tuple[Patient, bool]:
    nh_id = data["id"]
    nh_institution_id = data["institution_id"]
    defaults = {
        "nh_id": nh_id,
        "nh_institution_id": nh_institution_id,
        "nh_created_at": parse_nh_datetime_str(data["created_at"]),
        "nh_guarantor_id": data["guarantor_id"],
        "nh_inactive": data["inactive"],
        "nh_last_sync_time": parse_nh_datetime_str(data["last_sync_time"]),
        "nh_updated_at": parse_nh_datetime_str(data["updated_at"]),
        "balance_amount": data["balance"]["amount"] if data["balance"] else None,
        "balance_currency": data["balance"]["currency"] if data["balance"] else None,
        "bio": data["bio"],
        "email": data["email"],
        "first_name": data["first_name"],
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "last_name": data["last_name"],
        "middle_name": data["middle_name"],
        "name": data["name"],
        "unsubscribe_sms": data["unsubscribe_sms"],
        **get_phone_numbers_from_bio(data["bio"]),
    }

    # Payments, charges and adjustments are only optionally
    #   included in API responses. Don't set these if not included!
    for k in {"payments", "charges", "adjustments"}:
        if k in data:
            defaults[k] = data[k]

    with atomic():
        if should_create_or_update_related_insurances:
            InsuranceCoverage.objects.filter(nh_patient_id=nh_id, nh_institution_id=nh_institution_id).delete()
            for coverage_data in data.get("insurance_coverages", []):
                update_or_create_insurance_coverage_from_dict(coverage_data, nh_institution_id, should_create_or_update_related_insurance_plans=True)

        return Patient.objects.update_or_create(
            nh_id=nh_id,
            nh_institution_id=nh_institution_id,
            defaults=defaults,
        )


def update_or_create_appointment_from_dict(
    data: Dict, nh_institution_id: int, should_create_or_update_related_procedures: bool = False
) -> Tuple[Appointment, bool]:
    nh_id = data["id"]
    nh_location_id = data["location_id"]
    defaults = {
        "nh_id": nh_id,
        "nh_institution_id": nh_institution_id,
        "nh_location_id": nh_location_id,
        "nh_created_at": parse_nh_datetime_str(data["created_at"]),
        "nh_last_sync_time": parse_nh_datetime_str(data["last_sync_time"]),
        "nh_updated_at": parse_nh_datetime_str(data["updated_at"]),
        "nh_patient_id": data["patient_id"],
        "nh_provider_id": data["provider_id"],
        "nh_operatory_id": data["operatory_id"],
        "nh_deleted": data["deleted"],
        "cancelled": data["cancelled"],
        "cancelled_at": data["cancelled_at"],
        "checked_out": data["checked_out"],
        "checked_out_at": data["checked_out_at"],
        "checkin_at": data["checkin_at"],
        "confirmed": data["confirmed"],
        "confirmed_at": data["confirmed_at"],
        "end_time": parse_nh_datetime_str(data["end_time"]),
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "is_guardian": data["is_guardian"],
        "is_new_clients_patient": data["is_new_clients_patient"],
        "is_past_patient": data["is_past_patient"],
        "misc": data["misc"],
        "note": data["note"],
        "patient_confirmed": data["patient_confirmed"],
        "patient_confirmed_at": data["patient_confirmed_at"],
        "patient_missed": data["patient_missed"],
        "provider_name": data["provider_name"],
        "referrer": data["referrer"],
        "sooner_if_possible": data["sooner_if_possible"],
        "start_time": parse_nh_datetime_str(data["start_time"]),
        "timezone_offset": data["timezone_offset"],
        "unavailable": data["unavailable"],
    }
    with atomic():
        if should_create_or_update_related_procedures:
            for procedure_data in data.get("procedures", []):
                update_or_create_procedure_from_dict(procedure_data, nh_institution_id)

        return Appointment.objects.update_or_create(
            nh_id=nh_id,
            nh_institution_id=nh_institution_id,
            defaults=defaults,
        )


def update_or_create_procedure_from_dict(
    data: Dict,
    nh_institution_id: int,
) -> Tuple[Procedure, bool]:
    nh_id = data["id"]
    nh_appointment_id = data["appointment_id"]
    nh_patient_id = data["patient_id"]
    nh_provider_id = data["provider_id"]
    defaults = {
        "nh_appointment_id": nh_appointment_id,
        "nh_id": nh_id,
        "nh_patient_id": nh_patient_id,
        "nh_provider_id": nh_provider_id,
        "body_site": data["body_site"],
        "code": data["code"],
        "end_date": data["end_date"],
        "fee_amount": data["fee"]["amount"],
        "fee_currency": data["fee"]["currency"],
        "name": data["name"],
        "start_date": data["start_date"],
        "status": data["status"],
    }

    return Procedure.objects.update_or_create(
        nh_id=nh_id,
        nh_appointment_id=nh_appointment_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def update_or_create_provider_from_dict(data: Dict, synchronize_locations: bool = True) -> Tuple[Provider, bool]:
    nh_id = data["id"]
    nh_institution_id = data["institution_id"]
    defaults = {
        "nh_institution_id": nh_institution_id,
        "nh_id": nh_id,
        "nh_created_at": parse_nh_datetime_str(data["created_at"]),
        "nh_inactive": data["inactive"],
        "nh_last_sync_time": parse_nh_datetime_str(data["last_sync_time"]),
        "nh_updated_at": parse_nh_datetime_str(data["updated_at"]),
        "availabilities": data["availabilities"],
        "bio": data["bio"],
        "display_name": data["display_name"],
        "email": data["email"],
        "first_name": data["first_name"],
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "last_name": data["last_name"],
        "middle_name": data["middle_name"],
        "name": data["name"],
        "npi": data["npi"],
        **get_phone_numbers_from_bio(data["bio"]),
    }
    if synchronize_locations:
        LocationProvider.objects.filter(nh_institution_id=nh_institution_id, nh_provider_id=nh_id).delete()
        LocationProvider.objects.bulk_create(
            (
                LocationProvider(nh_provider_id=nh_id, nh_location_id=d["location_id"], nh_institution_id=nh_institution_id)
                for d in data.get("provider_requestables", [])
            )
        )

    return Provider.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def get_or_create_location_provider(
    nh_location_id: int,
    nh_provider_id: int,
    nh_institution_id: int,
) -> Tuple[LocationProvider, bool]:
    return LocationProvider.objects.get_or_create(
        nh_location_id=nh_location_id,
        nh_provider_id=nh_provider_id,
        nh_institution_id=nh_institution_id,
        defaults={
            "nh_location_id": nh_location_id,
            "nh_provider_id": nh_provider_id,
            "nh_institution_id": nh_institution_id,
        },
    )


def update_or_create_insurance_plan_from_dict(data: Dict, nh_institution_id: int) -> Tuple[InsurancePlan, bool]:
    nh_id = data["id"]
    defaults = {
        "nh_institution_id": nh_institution_id,
        "nh_id": nh_id,
        "country_code": data["country_code"],
        "state": data["state"],
        "address": data["address"],
        "address2": data["address2"],
        "city": data["city"],
        "zip_code": data["zip_code"],
        "name": data["name"],
        "payer_id": data["payer_id"],
        "group_num": data["group_num"],
        "employer_name": data["employer_name"],
        "foreign_id": data.get("foreign_id"),
    }

    return InsurancePlan.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def update_or_create_insurance_coverage_from_dict(
    data: Dict,
    nh_institution_id: int,
    should_create_or_update_related_insurance_plans: bool = False,
) -> Tuple[InsuranceCoverage, bool]:
    nh_id = data["id"]
    nh_patient_id = data["patient_id"]
    nh_insurance_plan_id = data["plan"]["id"]
    defaults = {
        "nh_institution_id": nh_institution_id,
        "nh_id": nh_id,
        "nh_patient_id": nh_patient_id,
        "nh_insurance_plan_id": nh_insurance_plan_id,
        "effective_date": data["effective_date"],
        "expiration_date": data["expiration_date"],
        "priority": data["priority"],
        "subscriber_num": data["subscriber_num"],
        "subscription_relation": data["subscription_relation"],
    }
    if should_create_or_update_related_insurance_plans:
        update_or_create_insurance_plan_from_dict(data["plan"], nh_institution_id)

    return InsuranceCoverage.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        nh_patient_id=nh_patient_id,
        defaults=defaults,
    )


def update_or_create_peerlogic_patient_from_nexhealth(
    nh_patient: Patient,
    peerlogic_practice: core_models.Practice,
) -> core_models.Patient:
    patient_data = {
        "date_of_birth": nh_patient.date_of_birth,
        "email": nh_patient.email,
        "is_active": not nh_patient.nh_inactive,
        "name": nh_patient.name,
        "name_first": nh_patient.first_name,
        "name_last": nh_patient.last_name,
        "name_middle": nh_patient.middle_name,
        "phone_home": nh_patient.phone_number_home,
        "phone_mobile": nh_patient.phone_number_mobile,
        "phone_number": nh_patient.phone_number,
        "phone_work": nh_patient.phone_number_work,
        "organization_id": peerlogic_practice.organization_id,
    }

    with atomic():
        # Check for an existing association based just on IDs
        existing_link = NexHealthPatientLink.objects.filter(nh_institution_id=nh_patient.nh_institution_id, nh_patient_id=nh_patient.nh_id).first()
        if existing_link:
            # Update the existing core.Patient record with new data
            peerlogic_patient = existing_link.peerlogic_patient
            if peerlogic_patient.modified_at > nh_patient.nh_updated_at:
                log.info(f"Not updating Patient {peerlogic_patient.id} due to existing data being more up-to-date")
                return peerlogic_patient

            for k, v in patient_data.items():
                setattr(peerlogic_patient, k, v)
            peerlogic_patient.save()
        else:
            # Check for matching core.Patient records based on other fields
            # TODO: For now, there is no other source of patient records
            #   so we can punt on this implementation for now and just
            #   always create the record (below)

            # Create a core.Patient record and NexHealthPatientLink
            peerlogic_patient = core_models.Patient.objects.create(**patient_data)

            NexHealthPatientLink.objects.create(
                nh_institution_id=nh_patient.nh_institution_id, nh_patient_id=nh_patient.nh_id, peerlogic_patient=peerlogic_patient
            )

        # Ensure practice association exists
        core_models.PracticePatient.objects.update_or_create(
            practice_id=peerlogic_practice.id,
            patient_id=peerlogic_patient.id,
            defaults={"practice_id": peerlogic_practice.id, "patient_id": peerlogic_patient.id},
        )

    return peerlogic_patient


def update_or_create_peerlogic_appointment_from_nexhealth(
    nh_appointment: Appointment,
    peerlogic_practice: core_models.Practice,
    procedures: Optional[Iterable[Procedure]] = None,
    peerlogic_patient: Optional[core_models.Patient] = None,
) -> core_models.Appointment:
    if peerlogic_patient is None:
        peerlogic_patient = NexHealthPatientLink.objects.get(
            nh_institution_id=nh_appointment.nh_institution_id, nh_patient_id=nh_appointment.nh_patient_id
        ).peerlogic_patient

    if procedures is None:
        procedures = Procedure.objects.filter(
            nh_institution_id=nh_appointment.nh_institution_id,
            nh_appointment_id=nh_appointment.nh_id,
        ).all()
    procedures_flattened = []
    fee_currency = None
    fee_total_amount = 0
    for procedure in procedures:
        fee_currency = procedure.fee_currency
        fee_amount = float(procedure.fee_amount)
        fee_total_amount += fee_amount
        procedures_flattened.append({"code": procedure.code, "name": procedure.name, "fee_currency": fee_currency, "fee_amount": fee_amount})

    status = core_models.Appointment.Status.SCHEDULED
    if nh_appointment.nh_deleted:
        status = core_models.Appointment.Status.DELETED
    if nh_appointment.cancelled:
        status = core_models.Appointment.Status.CANCELLED
    elif nh_appointment.end_time < timezone.now():
        status = core_models.Appointment.Status.COMPLETED

    is_active = nh_appointment.nh_deleted is False and nh_appointment.cancelled is False and nh_appointment.unavailable is False
    appointment_data = {
        "procedures": procedures_flattened,
        "appointment_start_at": nh_appointment.start_time,
        "appointment_end_at": nh_appointment.end_time,
        "patient_id": peerlogic_patient,  # Must be an instance, not an ID
        "practice_id": peerlogic_practice,  # Must be an instance, not an ID
        "status": status,
        "is_active": is_active,
        "approximate_total_currency": fee_currency or "USD",
        "approximate_total_amount": fee_total_amount,
        "is_new_patient": not nh_appointment.is_past_patient,
        "note": nh_appointment.note,
        "confirmed_at": nh_appointment.patient_confirmed_at if nh_appointment.patient_confirmed_at else nh_appointment.confirmed_at,
        "did_patient_miss": nh_appointment.patient_missed,
    }

    with atomic():
        existing_link = NexHealthAppointmentLink.objects.filter(
            nh_institution_id=nh_appointment.nh_institution_id, nh_appointment_id=nh_appointment.nh_id
        ).first()
        if existing_link:
            # Update the existing core.Appointment record with new data
            peerlogic_appointment = existing_link.peerlogic_appointment
            if peerlogic_appointment.modified_at > nh_appointment.nh_updated_at:
                log.info(f"Not updating Appointment {peerlogic_appointment.id} due to existing data being more up-to-date")
                return peerlogic_appointment

            for k, v in appointment_data.items():
                setattr(peerlogic_appointment, k, v)
            peerlogic_appointment.save()
        else:
            # Create and link a core.Appointment record
            peerlogic_appointment = core_models.Appointment.objects.create(**appointment_data)
            NexHealthAppointmentLink.objects.create(
                nh_institution_id=nh_appointment.nh_institution_id, nh_appointment_id=nh_appointment.nh_id, peerlogic_appointment=peerlogic_appointment
            )
    return peerlogic_appointment


def sync_nexhealth_records_for_practice(practice: core_models.Practice) -> None:
    """
    For the given Practice, this will iterate all NexHealth Patient and Appointment records with an updated_at
    greater than the given updated_since value and will update/create relevant Peerlogic Patient and Appointment records
    """
    locations = Location.objects.filter(peerlogic_practice=practice)
    institutions = Institution.objects.filter(nh_id__in=locations.values_list("nh_institution_id", flat=True)).distinct()

    for institution in institutions:
        now = timezone.now()
        updated_since = institution.synced_patients_to_peerlogic_at or timezone.now() - timedelta(days=30)
        log.info(
            f"Syncing patient records for Peerlogic Practice ({practice.id}), NexHealth Institution ({institution.nh_id}), updated_since ({updated_since.isoformat()})"
        )
        nh_patients = Patient.objects.filter(nh_institution_id=institution.nh_id, modified_at__gte=updated_since)
        log.info(
            f"Creating or updating {len(nh_patients)} patient records for Peerlogic Practice ({practice.id}), NexHealth Institution ({institution.nh_id}), updated_since ({updated_since.isoformat()})"
        )
        for nh_patient in nh_patients:
            update_or_create_peerlogic_patient_from_nexhealth(nh_patient, practice)
        log.info(
            f"Completed syncing patient records for Peerlogic Practice ({practice.id}), NexHealth Institution ({institution.nh_id}), updated_since ({updated_since.isoformat()})"
        )
        institution.synced_patients_to_peerlogic_at = now
        institution.save()

    for location in locations:
        now = timezone.now()
        updated_since = location.synced_appointments_to_peerlogic_at or timezone.now() - timedelta(days=30)
        nh_institution_id = location.nh_institution_id
        log.info(
            f"Syncing appointment records for Peerlogic Practice ({practice.id}), NexHealth Institution ({nh_institution_id}), NexHealth Location ({location.nh_id}), updated_since ({updated_since.isoformat()})"
        )
        nh_appointments = Appointment.objects.filter(nh_institution_id=nh_institution_id, nh_location_id=location.nh_id, modified_at__gte=updated_since)
        log.info(
            f"Creating or updating {len(nh_appointments)} appointment records for Peerlogic Practice ({practice.id}), NexHealth Institution ({nh_institution_id}), NexHealth Location ({location.nh_id}), updated_since ({updated_since.isoformat()})"
        )
        for nh_appointment in nh_appointments:
            update_or_create_peerlogic_appointment_from_nexhealth(nh_appointment, practice)
        log.info(
            f"Completed syncing appointment records for Peerlogic Practice ({practice.id}), NexHealth Institution ({nh_institution_id}), NexHealth Location ({location.nh_id}), updated_since ({updated_since.isoformat()})"
        )
        location.synced_appointments_to_peerlogic_at = now
        location.save()
