"""
Creates and updates nexhealth_integration models by making API requests to NexHealth for the given practice.
This function can be called to both initialize a practice, and to fetch updated data for a practice.

Once per practice, this is triggered manually by an API call to `POST /api/integrations/nexhealth/ingest-practice`. This initializes the practice.
After that, this function is typically triggered by the `/cron/nexhealth/update-practices` cron, which enqueues a Pub/Sub event per practice with
an active NexHealth integration on a regular interval.

Inputs:

peerlogic_practice_id: str - ShortUUID PK of the practice for which NexHealth data is to be ingested
appointment_created_at_from: isoformat_datetime_str - Datetime from which records will be pulled from NexHealth
appointment_created_at_to: isoformat_datetime_str - Datetime to which records will be pulled from NexHealth
is_institution_bound_to_practice: bool - If true, the nexhealth_integration.Institution record will link directly to the practice (typically false)
nexhealth_institution_id: int - ID of the Institution in NexHealth that corresponds to the practice
nexhealth_location_id: int - ID of the Location in NexHealth that corresponds to the practice
nexhealth_subdomain: str - Subdomain corresponding the the NexHealth Institution that corresponds to the practice
sync_records_when_complete: bool (default True) - If true, the `sync_practice` Cloud Function will be called for the practice at the end of the run
"""

import base64
import datetime
import json
import logging
import os
from concurrent import futures
from typing import Dict

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peerlogic.settings")
django.setup()

from core.models import Organization as PeerlogicOrganization
from core.models import Practice as PeerlogicPractice
from core.pubsub_helpers import publish_event
from nexhealth_integration.ingest import ingest_all_nexhealth_records_for_practice
from nexhealth_integration.utils import NexHealthLogAdapter
from peerlogic.settings import PUBSUB_TOPIC_PATH_NEXHEALTH_SYNC_PRACTICE

log = NexHealthLogAdapter(logging.getLogger(__name__))


def nexhealth_ingest_practice(event: Dict, context: Dict) -> None:
    log.info(f"Started nexhealth_ingest_practice! Event: {event}, Context: {context}")
    data = json.loads(base64.b64decode(event["data"]).decode())
    sync_records_when_complete = data.get("sync_records_when_complete", True)
    peerlogic_practice = PeerlogicPractice.objects.prefetch_related("organization").get(id=data["peerlogic_practice_id"])
    peerlogic_organization = peerlogic_practice.organization
    ingest_all_nexhealth_records_for_practice(
        appointment_created_at_from=datetime.datetime.fromisoformat(data["appointment_created_at_from"]),
        appointment_created_at_to=datetime.datetime.fromisoformat(data["appointment_created_at_to"]),
        is_institution_bound_to_practice=data["is_institution_bound_to_practice"],
        nexhealth_institution_id=data["nexhealth_institution_id"],
        nexhealth_location_id=data["nexhealth_location_id"],
        nexhealth_subdomain=data["nexhealth_subdomain"],
        peerlogic_organization=peerlogic_organization,
        peerlogic_practice=peerlogic_practice,
    )
    if sync_records_when_complete:
        log.info(f"Enqueueing nexhealth_sync_practice for PeerlogicPractice ({peerlogic_practice.id})")
        gcp_futures = [
            publish_event(
                event_attributes={},
                event={
                    "peerlogic_practice_id": peerlogic_practice.id,
                },
                topic_path=PUBSUB_TOPIC_PATH_NEXHEALTH_SYNC_PRACTICE,
            )
        ]
        futures.wait(gcp_futures)
    log.info(f"Completed nexhealth_ingest_practice!")


if __name__ == "__main__":
    practice = PeerlogicPractice.objects.get(id="39Zg3tQtHppG6jpx6jSxc6")
    organization = PeerlogicOrganization.objects.get(id="QDuCEPfRwuScig7YxBvstG")

    ingest_all_nexhealth_records_for_practice(
        nexhealth_institution_id=4047,
        nexhealth_subdomain="peerlogic-od-sandbox",
        nexhealth_location_id=25663,
        peerlogic_practice=practice,
        peerlogic_organization=organization,
        is_institution_bound_to_practice=False,
        appointment_created_at_from=datetime.datetime.strptime("2022-12-01", "%Y-%M-%d"),
        appointment_created_at_to=datetime.datetime.strptime("2023-03-01", "%Y-%M-%d"),
    )
