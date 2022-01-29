from concurrent import futures
import json
import logging
from typing import Dict, List

from django.conf import settings
from google.cloud import pubsub_v1

from core import pubsub_helpers

# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_leg_b_ready_cdrs(
    netsapiens_call_subscription_id: str,
    practice_id: str,
    voip_provider_id: str,
    event_data: List[Dict],
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_leg_b_finished=settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED
):

    publish_futures = []
    cdrs_to_publish = []  # for logging

    for cdr in event_data:
        # One of the leg-b's is finished only when these requirements are true,
        # otherwise the leg-b is still on-going and hasn't been finished yet.
        if not (cdr.get("remove") == "yes" and cdr.get("term_leg_tag")):
            continue

        cdr_encode_data = json.dumps(cdr, indent=2).encode("utf-8")
        event_attributes = {
            "netsapiens_call_subscription_id": netsapiens_call_subscription_id,
            "practice_id": practice_id,
            "voip_provider_id": voip_provider_id,
        }

        # When you publish a message, the client returns a future.
        publish_future = publisher.publish(topic=topic_path_leg_b_finished, data=cdr_encode_data, **event_attributes)
        # Non-blocking. Publish failures are handled in the callback function.
        publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, cdr_encode_data))
        publish_futures.append(publish_future)
        cdrs_to_publish.append(cdr)

    log.info(f"Published messages {cdrs_to_publish} with error handler to {topic_path_leg_b_finished}.")
    return publish_futures
