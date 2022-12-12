import datetime
import logging
import os
from typing import Optional

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peerlogic.settings")
django.setup()

from core.models import Organization, Practice
from nexhealth_integration import adapters
from nexhealth_integration.nexhealth_api_client import NexHealthAPIClient
from nexhealth_integration.utils import NexHealthLogAdapter
from peerlogic.settings import (
    NEXHEALTH_API_ROOT_URL,
    NEXHEALTH_API_TOKEN,
    NEXHEALTH_PAGE_SIZE,
)

log = NexHealthLogAdapter(logging.getLogger(__name__))


def initialize_nexhealth_records_for_practice(
    nexhealth_institution_id: int,
    nexhealth_subdomain: str,
    nexhealth_location_id: int,
    peerlogic_organization: Organization,
    peerlogic_practice: Practice,
    is_institution_bound_to_practice: bool,
    appointment_start_time: datetime.datetime,
    appointment_end_time: datetime.datetime,
) -> None:
    client = _construct_nexhealth_api_client(nexhealth_institution_id, nexhealth_subdomain, nexhealth_location_id)
    _initialize_institution(client, peerlogic_practice, peerlogic_organization if is_institution_bound_to_practice else None)
    _initialize_location(client, peerlogic_practice)
    _initialize_insurance_plans(client)
    _initialize_providers(client)
    _initialize_patients_and_insurance_coverages(client)
    _initialize_appointments(client, appointment_start_time, appointment_end_time)
    # TODO Kyle:
    #   Loop through and try to associate patients


def _construct_nexhealth_api_client(institution_id: int, subdomain: str, location_id: int) -> NexHealthAPIClient:
    log.info("Creating NexHealthAPIClient.")
    client = NexHealthAPIClient(NEXHEALTH_API_ROOT_URL, NEXHEALTH_API_TOKEN, institution_id, location_id, subdomain, NEXHEALTH_PAGE_SIZE)
    log.info("Created NexHealthAPIClient.")
    return client


def _initialize_institution(client: NexHealthAPIClient, practice: Practice, organization: Optional[Organization]) -> None:
    log.info("Creating or updating Institution.")
    r = client.get_institution()
    institution, institution_created = adapters.create_or_update_institution_from_dict(
        r.response_nh_data, peerlogic_organization=organization, peerlogic_practice=practice
    )
    log.info(f"Institution ({institution.id}) for NexHealth Institution {institution.nh_id} successfully {'created' if institution_created else 'updated'}!")


def _initialize_location(client: NexHealthAPIClient, practice: Practice) -> None:
    log.info("Creating or updating Location.")
    r = client.get_location()
    location, location_created = adapters.create_or_update_location_from_dict(r.response_nh_data, peerlogic_practice=practice)
    log.info(f"Location ({location.id}) for NexHealth Location {location.nh_id} successfully {'created' if location_created else 'updated'}!")


def _initialize_insurance_plans(client: NexHealthAPIClient) -> None:
    log.info("Creating or updating InsurancePlans.")
    r = client.list_insurance_plans()
    created = 0
    updated = 0
    for insurance_plan_data in r.response_nh_data:
        _, was_created = adapters.create_or_update_insurance_plan_from_dict(insurance_plan_data, r.client_nh_institution_id)
        if was_created:
            created += 1
        else:
            updated += 1
    log.info(f"Created {created} and updated {updated} InsurancePlans!")


def _initialize_providers(client: NexHealthAPIClient) -> None:
    log.info("Creating or updating Providers (and ProviderLocations).")
    r = client.list_providers()
    created = 0
    updated = 0
    for provider_data in r.response_nh_data:
        _, was_created = adapters.create_or_update_provider_from_dict(provider_data)
        if was_created:
            created += 1
        else:
            updated += 1
    # TODO Kyle: ProviderLocations
    log.info(f"Created {created} and updated {updated} Providers!")


def _initialize_patients_and_insurance_coverages(client: NexHealthAPIClient) -> None:
    log.info("Creating or updating Patients (and Insurance Coverages).")
    r = client.list_patients()
    created = 0
    updated = 0
    for patient_data in r.response_nh_data["patients"]:
        _, was_created = adapters.create_or_update_patient_from_dict(patient_data, create_or_update_related_insurances=True)
        if was_created:
            created += 1
        else:
            updated += 1
    log.info(f"Created {created} and updated {updated} Patients!")


def _initialize_appointments(client: NexHealthAPIClient, appointment_start_time: datetime.datetime, appointment_end_time: datetime.datetime) -> None:
    log.info("Creating or updating Appointments (and Procedures).")
    r = client.list_appointments(
        start_time=appointment_start_time,
        end_time=appointment_end_time,
    )
    created = 0
    updated = 0
    for appointment_data in r.response_nh_data:
        _, was_created = adapters.create_or_update_appointment_from_dict(
            appointment_data, nh_institution_id=r.client_nh_institution_id, create_or_update_related_procedures=True
        )
        if was_created:
            created += 1
        else:
            updated += 1
    log.info(f"Created {created} and updated {updated} Appointments!")


if __name__ == "__main__":
    practice = Practice.objects.get(id="39Zg3tQtHppG6jpx6jSxc6")
    organization = Organization.objects.get(id="QDuCEPfRwuScig7YxBvstG")

    initialize_nexhealth_records_for_practice(
        nexhealth_institution_id=4047,
        nexhealth_subdomain="peerlogic-od-sandbox",
        nexhealth_location_id=25229,
        peerlogic_practice=practice,
        peerlogic_organization=organization,
        is_institution_bound_to_practice=False,
        appointment_start_time=datetime.datetime.strptime("2022-12-01", "%Y-%M-%d"),
        appointment_end_time=datetime.datetime.strptime("2023-01-01", "%Y-%M-%d"),
    )
