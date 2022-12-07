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


def create_or_update_procedure_from_dict(
    data: Dict,
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
