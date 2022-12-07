from typing import Dict, Optional, Tuple

from core import models as core_models
from nexhealth_integration.models import (
    APIRequest,
    Appointment,
    Institution,
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
        nh_appointment_id=nh_appointment_id,
        nh_id=nh_id,
        defaults=defaults,
    )
