import datetime
import logging
from typing import Optional

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


def ingest_all_nexhealth_records_for_practice(
    appointment_end_time: datetime.datetime,
    appointment_start_time: datetime.datetime,
    is_institution_bound_to_practice: bool,
    nexhealth_institution_id: int,
    nexhealth_location_id: int,
    nexhealth_subdomain: str,
    peerlogic_organization: PeerlogicOrganization,
    peerlogic_practice: PeerlogicPractice,
) -> None:
    """
    Ingest NexHealth records for resources pertaining to the given Practice/Organization.

    If resources for the given NexHealth Location have been ingested before, records will be filtered on updated_since.
    """
    log.info(
        f"Ingesting NexHealth resources for NexHealth Institution ({nexhealth_institution_id}), "
        f"SubDomain ('{nexhealth_subdomain}'), Location ({nexhealth_location_id}), and Peerlogic "
        f"Organization: {peerlogic_organization.name} ({peerlogic_organization.id}), "
        f"Practice: {peerlogic_practice.name} ({peerlogic_practice.id}). NexHealth institution will be bound to "
        f"{'practice' if is_institution_bound_to_practice else 'organization'}."
    )
    location_updated_at = datetime.datetime.utcnow()
    client = _construct_nexhealth_api_client(nexhealth_institution_id, nexhealth_subdomain, nexhealth_location_id)
    _ingest_institution(client, peerlogic_practice, peerlogic_organization if is_institution_bound_to_practice else None)
    location = _ingest_location(client, peerlogic_practice)
    if location.updated_from_nexhealth_at is None:
        # Only index all insurance plans the first time we ingest data for the location
        # After this, we'll keep everything up-to-date as we pull in patients
        _ingest_insurance_plans(client)
    else:
        log.info(
            f"NexHealth resources for  Location ({nexhealth_location_id}) have been ingested before. "
            f"Filtering updated_since={location.updated_from_nexhealth_at}"
        )
        log.info(
            "Not ingesting InsurancePlans since this Location has been previously ingested. InsurancePlans will be ingested as we ingest updated patients."
        )

    _ingest_providers(client, updated_since=location.updated_from_nexhealth_at)
    _ingest_patients_and_insurance_coverages(client, updated_since=location.updated_from_nexhealth_at)
    _ingest_appointments(client, appointment_start_time, appointment_end_time, updated_since=location.updated_from_nexhealth_at)
    _mark_location_updated(location, location_updated_at)
    log.info(
        f"Completed ingesting NexHealth resources for NexHealth Institution ({nexhealth_institution_id}), "
        f"SubDomain ('{nexhealth_subdomain}'), Location ({nexhealth_location_id}), and Peerlogic "
        f"Organization: {peerlogic_organization.name} ({peerlogic_organization.id}), "
        f"Practice: {peerlogic_practice.name} ({peerlogic_practice.id}). NexHealth institution is bound to "
        f"{'practice' if is_institution_bound_to_practice else 'organization'}."
    )


def _mark_location_updated(
    location: Location,
    updated_from_nexhealth_at: datetime.datetime,
):
    log.info(f"Updating Location ({location.id}) is_initialized=True, updated_from_nexhealth_at={updated_from_nexhealth_at.isoformat()}")
    location.updated_from_nexhealth_at = updated_from_nexhealth_at
    location.is_initialized = True
    location.save()


def _construct_nexhealth_api_client(institution_id: int, subdomain: str, location_id: int) -> NexHealthAPIClient:
    log.info("Creating NexHealthAPIClient.")
    client = NexHealthAPIClient(NEXHEALTH_API_ROOT_URL, NEXHEALTH_API_TOKEN, institution_id, location_id, subdomain, NEXHEALTH_PAGE_SIZE)
    log.info("Created NexHealthAPIClient.")
    return client


def _ingest_institution(client: NexHealthAPIClient, practice: PeerlogicPractice, organization: Optional[PeerlogicOrganization]) -> None:
    log.info("Ingesting Institution")
    r = client.get_institution()
    institution, institution_created = adapters.update_or_create_institution_from_dict(
        r.response_nh_data, peerlogic_organization=organization, peerlogic_practice=practice
    )
    log.info(f"Institution ({institution.id}) for NexHealth Institution {institution.nh_id} successfully {'created' if institution_created else 'updated'}!")


def _ingest_location(client: NexHealthAPIClient, practice: PeerlogicPractice) -> Location:
    log.info("Ingesting Location")
    r = client.get_location()
    location, location_created = adapters.update_or_create_location_from_dict(r.response_nh_data, peerlogic_practice=practice)
    log.info(f"Location ({location.id}) for NexHealth Location {location.nh_id} successfully {'created' if location_created else 'updated'}!")
    return location


def _ingest_insurance_plans(client: NexHealthAPIClient) -> None:
    log.info("Ingesting InsurancePlans")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_insurance_plans):
        for insurance_plan_data in r.response_nh_data:
            _, was_created = adapters.update_or_create_insurance_plan_from_dict(insurance_plan_data, r.client_nh_institution_id)
            if was_created:
                created += 1
            else:
                updated += 1
    log.info(f"InsurancePlans: created={created}, updated={updated}")


def _ingest_providers(client: NexHealthAPIClient, updated_since: Optional[datetime.datetime]) -> None:
    log.info("Ingesting Providers (and ProviderLocations)")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_providers, updated_since=updated_since):
        for provider_data in r.response_nh_data:
            _, was_created = adapters.update_or_create_provider_from_dict(provider_data)
            if was_created:
                created += 1
            else:
                updated += 1
    log.info(f"Providers: created={created}, updated={updated}")


def _ingest_patients_and_insurance_coverages(client: NexHealthAPIClient, updated_since: Optional[datetime.datetime] = None) -> None:
    log.info("Ingesting Patients (and Insurance Coverages)")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(client.list_patients, updated_since=updated_since):
        for patient_data in r.response_nh_data["patients"]:
            patient, was_created = adapters.update_or_create_patient_from_dict(patient_data, should_create_or_update_related_insurances=True)
            if was_created:
                created += 1
            else:
                updated += 1
    log.info(f"Patients: created={created}, updated={updated}")


def _ingest_appointments(
    client: NexHealthAPIClient,
    appointment_start_time: datetime.datetime,
    appointment_end_time: datetime.datetime,
    updated_since: Optional[datetime.datetime] = None,
) -> None:
    log.info("Ingesting Appointments (and Procedures)")
    created = 0
    updated = 0
    for r in client.iterate_list_requests(
        client.list_appointments, start_time=appointment_start_time, end_time=appointment_end_time, updated_since=updated_since
    ):
        for appointment_data in r.response_nh_data:
            _, was_created = adapters.update_or_create_appointment_from_dict(
                appointment_data, nh_institution_id=r.client_nh_institution_id, should_create_or_update_related_procedures=True
            )
            if was_created:
                created += 1
            else:
                updated += 1
    log.info(f"Appointments: created={created}, updated={updated}")
