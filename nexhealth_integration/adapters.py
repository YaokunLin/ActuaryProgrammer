from typing import Dict, Optional, Tuple

from core import models as core_models
from nexhealth_integration.models import (
    APIRequest,
    Appointment,
    Institution,
    Location,
    Patient,
    Procedure,
    Provider,
)
from nexhealth_integration.utils import (
    get_best_phone_number_from_bio,
    parse_nh_datetime_str,
)


def create_or_update_institution_from_dict(
    data: Dict,
    peerlogic_organization: Optional[core_models.Organization] = None,
    peerlogic_practice: Optional[core_models.Practice] = None,
) -> Tuple[Institution, bool]:
    nh_id = data["id"]
    defaults = {
        "nh_id": nh_id,
        "appointment_types_location_scoped": data["appointment_types_location_scoped"],
        "country_code": data["country_code"],
        "emrs": data["emrs"],
        "is_appt_categories_location_specific": data["is_appt_categories_location_specific"],
        "is_sync_notifications": data["is_sync_notifications"],
        "name": data["name"],
        "notify_insert_fails": data["notify_insert_fails"],
        "phone_number": data["phone_number"],
        "subdomain": data["subdomain"],
    }
    if peerlogic_organization:
        defaults["peerlogic_organization_id"] = peerlogic_organization.id
    if peerlogic_practice:
        defaults["peerlogic_practice_id"] = peerlogic_practice.id

    return Institution.objects.update_or_create(
        nh_id=nh_id,
        defaults=defaults,
    )


def create_or_update_location_from_dict(
    data: Dict,
    institution: Optional[Institution] = None,
    peerlogic_practice: Optional[core_models.Practice] = None,
) -> Tuple[Location, bool]:
    nh_id = data["id"]
    nh_institution_id = data["institution_id"]
    defaults = {
        "nh_id": nh_id,
        "nh_institution_id": nh_institution_id,
        "nh_created_at": data["created_at"],
        "nh_inactive": data["inactive"],
        "nh_last_sync_time": data["last_sync_time"],
        "nh_updated_at": data["updated_at"],
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
    if institution:
        defaults["institution_id"] = institution.id
    if peerlogic_practice:
        defaults["peerlogic_practice_id"] = peerlogic_practice.id

    return Location.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def create_or_update_patient_from_dict(
    data: Dict,
    institution: Optional[Institution] = None,
    guarantor: Optional[Patient] = None,
) -> Tuple[Patient, bool]:
    nh_id = data["id"]
    nh_institution_id = data["institution_id"]
    defaults = {
        "nh_id": nh_id,
        "nh_institution_id": nh_institution_id,
        "nh_created_at": data["created_at"],
        "nh_guarantor_id": data["guarantor_id"],
        "nh_inactive": data["inactive"],
        "nh_last_sync_time": data["last_sync_time"],
        "nh_updated_at": data["updated_at"],
        "balance_amount": data["balance"]["amount"] if data["balance"] else None,
        "balance_currency": data["balance"]["currency"] if data["balance"] else None,
        "bio": data["bio"],
        "first_name": data["first_name"],
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "last_name": data["last_name"],
        "middle_name": data["middle_name"],
        "name": data["name"],
        "phone_number": get_best_phone_number_from_bio(data["bio"]),
        "unsubscribe_sms": data["unsubscribe_sms"],
    }
    if institution is not None:
        defaults["institution_id"] = institution.id
    if guarantor is not None:
        defaults["guarantor_id"] = guarantor.id

    # Payments, charges and adjustments are only optionally
    #   included in API responses. Don't set these if not included!
    for k in {"payments", "charges", "adjustments"}:
        if k in data:
            defaults[k] = data[k]

    return Patient.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def create_or_update_appointment_from_dict(
    data: Dict,
    nh_institution_id: int,
    location: Optional[Location] = None,
    provider: Optional[Provider] = None,
    patient: Optional[Patient] = None,
) -> Tuple[Appointment, bool]:
    nh_id = data["id"]
    nh_location_id = data["location_id"]
    defaults = {
        "nh_id": nh_id,
        "nh_institution_id": nh_institution_id,
        "nh_location_id": nh_location_id,
        "nh_created_at": data["created_at"],
        "nh_last_sync_time": data["last_sync_time"],
        "nh_updated_at": data["updated_at"],
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
    if location is not None:
        defaults["location_id"] = location.id
    if provider is not None:
        defaults["provider_id"] = provider.id
    if patient is not None:
        defaults["patient_id"] = patient.id

    return Appointment.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def create_or_update_procedure_from_dict(
    data: Dict,
    nh_institution_id: int,
    appointment: Optional[Appointment] = None,
    patient: Optional[Patient] = None,
    provider: Optional[Provider] = None,
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
    if appointment and appointment.nh_id == nh_appointment_id:
        defaults["appointment_id"] = appointment.id
    if patient and patient.nh_id == nh_patient_id:
        defaults["patient_id"] = patient.id
    if provider and provider.nh_id == nh_provider_id:
        defaults["provider_id"] = provider.id

    return Procedure.objects.update_or_create(
        nh_id=nh_id,
        nh_appointment_id=nh_appointment_id,
        defaults=defaults,
    )


# TODO Kyle: Should all IDs just be unique with institution ultimately? I think so.
