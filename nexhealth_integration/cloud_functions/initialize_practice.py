import base64
import datetime
import json
import logging
import os
from typing import Dict

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peerlogic.settings")
django.setup()

from core.models import Organization as PeerlogicOrganization
from core.models import Practice as PeerlogicPractice
from nexhealth_integration.ingest import _ingest_all_nexhealth_records_for_practice
from nexhealth_integration.utils import NexHealthLogAdapter

log = NexHealthLogAdapter(logging.getLogger(__name__))


def nexhealth_initialize_practice(event: Dict, context: Dict) -> None:
    log.info(f"Started nexhealth_initialize_practice! Event: {event}, Context: {context}")
    data = json.loads(base64.b64decode(event["data"]).decode())
    peerlogic_practice = PeerlogicPractice.objects.get(id=data["peerlogic_practice_id"])
    peerlogic_organization = PeerlogicOrganization.objects.get(id=data["peerlogic_organization_id"])
    _ingest_all_nexhealth_records_for_practice(
        appointment_end_time=datetime.datetime.fromisoformat(data["appointment_end_time"]),
        appointment_start_time=datetime.datetime.fromisoformat(data["appointment_start_time"]),
        is_institution_bound_to_practice=data["is_institution_bound_to_practice"],
        nexhealth_institution_id=data["nexhealth_institution_id"],
        nexhealth_location_id=data["nexhealth_location_id"],
        nexhealth_subdomain=data["nexhealth_subdomain"],
        peerlogic_organization=peerlogic_practice,
        peerlogic_practice=peerlogic_organization,
    )
    log.info(f"Completed nexhealth_initialize_practice!")


if __name__ == "__main__":
    practice = PeerlogicPractice.objects.get(id="39Zg3tQtHppG6jpx6jSxc6")
    organization = PeerlogicOrganization.objects.get(id="QDuCEPfRwuScig7YxBvstG")

    _ingest_all_nexhealth_records_for_practice(
        nexhealth_institution_id=4047,
        nexhealth_subdomain="peerlogic-od-sandbox",
        nexhealth_location_id=25229,
        peerlogic_practice=practice,
        peerlogic_organization=organization,
        is_institution_bound_to_practice=False,
        appointment_start_time=datetime.datetime.strptime("2022-12-01", "%Y-%M-%d"),
        appointment_end_time=datetime.datetime.strptime("2023-01-01", "%Y-%M-%d"),
    )
