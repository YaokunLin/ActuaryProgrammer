from typing import Dict, Optional, Tuple

from django.db.transaction import atomic

from core import models as core_models
from nexhealth_integration.models import (
    APIRequest,
    Appointment,
    Institution,
    InsuranceCoverage,
    InsurancePlan,
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


def create_or_update_location_from_dict(
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


def create_or_update_patient_from_dict(data: Dict, create_or_update_related_insurances: bool = False) -> Tuple[Patient, bool]:
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
        "first_name": data["first_name"],
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "last_name": data["last_name"],
        "middle_name": data["middle_name"],
        "name": data["name"],
        "phone_number": get_best_phone_number_from_bio(data["bio"]),
        "unsubscribe_sms": data["unsubscribe_sms"],
    }

    # Payments, charges and adjustments are only optionally
    #   included in API responses. Don't set these if not included!
    for k in {"payments", "charges", "adjustments"}:
        if k in data:
            defaults[k] = data[k]

    with atomic():
        if create_or_update_related_insurances:
            InsuranceCoverage.objects.filter(nh_patient_id=nh_id, nh_institution_id=nh_institution_id).delete()
            for coverage_data in data.get("insurance_coverages", []):
                create_or_update_insurance_coverage_from_dict(coverage_data, nh_institution_id, create_or_update_related_insurance_plans=True)

        return Patient.objects.update_or_create(
            nh_id=nh_id,
            nh_institution_id=nh_institution_id,
            defaults=defaults,
        )


def create_or_update_appointment_from_dict(data: Dict, nh_institution_id: int, create_or_update_related_procedures: bool = False) -> Tuple[Appointment, bool]:
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
        if create_or_update_related_procedures:
            for procedure_data in data.get("procedures", []):
                create_or_update_procedure_from_dict(procedure_data, nh_institution_id)

        return Appointment.objects.update_or_create(
            nh_id=nh_id,
            nh_institution_id=nh_institution_id,
            defaults=defaults,
        )


def create_or_update_procedure_from_dict(
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


def create_or_update_provider_from_dict(
    data: Dict,
) -> Tuple[Provider, bool]:
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
        "phone_number": get_best_phone_number_from_bio(data["bio"]),
        "display_name": data["display_name"],
        "email": data["email"],
        "first_name": data["first_name"],
        "foreign_id": data["foreign_id"],
        "foreign_id_type": data["foreign_id_type"],
        "last_name": data["last_name"],
        "middle_name": data["middle_name"],
        "name": data["name"],
        "npi": data["npi"],
    }

    return Provider.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        defaults=defaults,
    )


def create_or_update_insurance_plan_from_dict(data: Dict, nh_institution_id: int) -> Tuple[InsurancePlan, bool]:
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


def create_or_update_insurance_coverage_from_dict(
    data: Dict,
    nh_institution_id: int,
    create_or_update_related_insurance_plans: bool = False,
) -> Tuple[InsuranceCoverage, bool]:
    nh_id = data["id"]
    nh_patient_id = data["patient_id"]
    nh_insurance_plan_id = data["plan"]["id"]
    defaults = {
        "nh_institution_id": nh_institution_id,
        "nh_id": nh_id,
        "nh_patient_id": nh_patient_id,
        "nh_insurance_plan_id": nh_insurance_plan_id,
        "effective_date": data["effective_date"],  # TODO Kyle: Type
        "expiration_date": data["expiration_date"],  # TODO Kyle: Type
        "priority": data["priority"],
        "subscriber_num": data["subscriber_num"],
        "subscription_relation": data["subscription_relation"],
    }
    if create_or_update_related_insurance_plans:
        create_or_update_insurance_plan_from_dict(data["plan"], nh_institution_id)

    return InsuranceCoverage.objects.update_or_create(
        nh_id=nh_id,
        nh_institution_id=nh_institution_id,
        nh_patient_id=nh_patient_id,
        defaults=defaults,
    )
