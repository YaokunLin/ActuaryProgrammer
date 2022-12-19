import datetime
import logging
import os
from typing import Dict, Optional

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peerlogic.settings")
django.setup()

from core.models import Organization as PeerlogicOrganization
from core.models import Practice as PeerlogicPractice
from nexhealth_integration import adapters
from nexhealth_integration.models import Location
from nexhealth_integration.nexhealth_api_client import NexHealthAPIClient
from nexhealth_integration.utils import NexHealthLogAdapter
from peerlogic.settings import (
    NEXHEALTH_API_ROOT_URL,
    NEXHEALTH_API_TOKEN,
    NEXHEALTH_PAGE_SIZE,
)

log = NexHealthLogAdapter(logging.getLogger(__name__))


def nexhealth_initialize_practice(event: Dict, context: Dict) -> None:
    log.info(f"Started nexhealth_initialize_practice! Event: {event}, Context: {context}")
    # TODO Kyle
    log.info(f"Completed nexhealth_initialize_practice!")


def _initialize_nexhealth_records_for_practice(
    nexhealth_institution_id: int,
    nexhealth_subdomain: str,
    nexhealth_location_id: int,
    peerlogic_organization: PeerlogicOrganization,
    peerlogic_practice: PeerlogicPractice,
    is_institution_bound_to_practice: bool,
    appointment_start_time: datetime.datetime,
    appointment_end_time: datetime.datetime,
) -> None:
    """
    Create/Update NexHealth DB records for resources pertaining to the given Practice/Organization
    """

    log.info(
        f"Initializing NexHealth Integration resources for NexHealth Institution ({nexhealth_institution_id}), "
        f'SubDomain ("{nexhealth_subdomain}"), Location ({nexhealth_location_id}), and Peerlogic '
        f"Organization: {peerlogic_organization.name} ({peerlogic_organization.id}), "
        f"Practice: {peerlogic_practice.name} ({peerlogic_practice.id}). NexHealth institution will be bound to "
        f"{'practice' if is_institution_bound_to_practice else 'organization'}."
    )
    client = _construct_nexhealth_api_client(nexhealth_institution_id, nexhealth_subdomain, nexhealth_location_id)
    _initialize_institution(client, peerlogic_practice, peerlogic_organization if is_institution_bound_to_practice else None)
    location = _initialize_location(client, peerlogic_practice)
    _initialize_insurance_plans(client)
    _initialize_providers(client)
    _initialize_patients_and_insurance_coverages(client, location, peerlogic_practice)
    _initialize_appointments(client, appointment_start_time, appointment_end_time)
    log.info(
        f"Completed initialization of NexHealth Integration resources for NexHealth Institution ({nexhealth_institution_id}), "
        f'SubDomain ("{nexhealth_subdomain}"), Location ({nexhealth_location_id}), and Peerlogic '
        f"Organization: {peerlogic_organization.name} ({peerlogic_organization.id}), "
        f"Practice: {peerlogic_practice.name} ({peerlogic_practice.id}). NexHealth institution is bound to "
        f"{'practice' if is_institution_bound_to_practice else 'organization'}."
    )


def _construct_nexhealth_api_client(institution_id: int, subdomain: str, location_id: int) -> NexHealthAPIClient:
    log.info("Creating NexHealthAPIClient.")
    client = NexHealthAPIClient(NEXHEALTH_API_ROOT_URL, NEXHEALTH_API_TOKEN, institution_id, location_id, subdomain, NEXHEALTH_PAGE_SIZE)
    log.info("Created NexHealthAPIClient.")
    return client


def _initialize_institution(client: NexHealthAPIClient, practice: PeerlogicPractice, organization: Optional[PeerlogicOrganization]) -> None:
    log.info("Creating or updating Institution.")
    r = client.get_institution()
    institution, institution_created = adapters.update_or_create_institution_from_dict(
        r.response_nh_data, peerlogic_organization=organization, peerlogic_practice=practice
    )
    log.info(f"Institution ({institution.id}) for NexHealth Institution {institution.nh_id} successfully {'created' if institution_created else 'updated'}!")


def _initialize_location(client: NexHealthAPIClient, practice: PeerlogicPractice) -> Location:
    log.info("Creating or updating Location.")
    r = client.get_location()
    location, location_created = adapters.update_or_create_location_from_dict(r.response_nh_data, peerlogic_practice=practice)
    log.info(f"Location ({location.id}) for NexHealth Location {location.nh_id} successfully {'created' if location_created else 'updated'}!")
    return location


def _initialize_insurance_plans(client: NexHealthAPIClient) -> None:
    log.info("Creating or updating InsurancePlans.")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_insurance_plans):
        for insurance_plan_data in r.response_nh_data:
            _, was_created = adapters.update_or_create_insurance_plan_from_dict(insurance_plan_data, r.client_nh_institution_id)
            if was_created:
                created += 1
            else:
                updated += 1
    log.info(f"Created {created} and updated {updated} InsurancePlans!")


def _initialize_providers(client: NexHealthAPIClient) -> None:
    log.info("Creating or updating Providers (and ProviderLocations).")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_providers):
        for provider_data in r.response_nh_data:
            _, was_created = adapters.update_or_create_provider_from_dict(provider_data)
            if was_created:
                created += 1
            else:
                updated += 1

    log.info(f"Created {created} and updated {updated} Providers!")


def _initialize_patients_and_insurance_coverages(client: NexHealthAPIClient, location: Location, peerlogic_practice: PeerlogicPractice) -> None:
    log.info("Creating or updating Patients (and Insurance Coverages).")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_patients):
        for patient_data in r.response_nh_data["patients"]:
            patient, was_created = adapters.update_or_create_patient_from_dict(patient_data, create_or_update_related_insurances=True)
            if was_created:
                created += 1
            else:
                updated += 1

    log.info(f"Created {created} and updated {updated} Patients!")


def _initialize_appointments(client: NexHealthAPIClient, appointment_start_time: datetime.datetime, appointment_end_time: datetime.datetime) -> None:
    log.info("Creating or updating Appointments (and Procedures).")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_appointments, start_time=appointment_start_time, end_time=appointment_end_time):
        for appointment_data in r.response_nh_data:
            _, was_created = adapters.update_or_create_appointment_from_dict(
                appointment_data, nh_institution_id=r.client_nh_institution_id, create_or_update_related_procedures=True
            )
            if was_created:
                created += 1
            else:
                updated += 1
    log.info(f"Created {created} and updated {updated} Appointments!")


if __name__ == "__main__":
    practice = PeerlogicPractice.objects.get(id="39Zg3tQtHppG6jpx6jSxc6")
    organization = PeerlogicOrganization.objects.get(id="QDuCEPfRwuScig7YxBvstG")

    _initialize_nexhealth_records_for_practice(
        nexhealth_institution_id=4047,
        nexhealth_subdomain="peerlogic-od-sandbox",
        nexhealth_location_id=25229,
        peerlogic_practice=practice,
        peerlogic_organization=organization,
        is_institution_bound_to_practice=False,
        appointment_start_time=datetime.datetime.strptime("2022-12-01", "%Y-%M-%d"),
        appointment_end_time=datetime.datetime.strptime("2023-01-01", "%Y-%M-%d"),
    )
