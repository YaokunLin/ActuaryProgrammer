import base64
import json
import logging
import os
from typing import Dict

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peerlogic.settings")
django.setup()

from core.models import Practice as PeerlogicPractice
from nexhealth_integration.adapters import sync_nexhealth_records_for_practice
from nexhealth_integration.utils import NexHealthLogAdapter

log = NexHealthLogAdapter(logging.getLogger(__name__))


def nexhealth_sync_patients_and_appointments_for_practice(event: Dict, context: Dict) -> None:
    log.info(f"Started nexhealth_sync_patients_and_appointments_for_practice! Event: {event}, Context: {context}")
    data = json.loads(base64.b64decode(event["data"]).decode())
    peerlogic_practice = PeerlogicPractice.objects.get(id=data["peerlogic_practice_id"])
    sync_nexhealth_records_for_practice(peerlogic_practice)
    log.info(f"Completed nexhealth_sync_patients_and_appointments_for_practice!")


if __name__ == "__main__":
    practice = PeerlogicPractice.objects.get(id="39Zg3tQtHppG6jpx6jSxc6")
    sync_nexhealth_records_for_practice(practice)
