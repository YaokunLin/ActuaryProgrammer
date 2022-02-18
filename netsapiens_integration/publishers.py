from datetime import (
    date,
    datetime,
    timedelta,
)
import json
import logging
from typing import Dict, List

from django.conf import settings
from django.db import models
from google.cloud import pubsub_v1

from core import pubsub_helpers


# Get an instance of a logger
log = logging.getLogger(__name__)


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)
    if isinstance(obj, models.Model):
        return obj.id

    raise TypeError(f"Type {type(obj)} not serializable")


def publish_leg_b_ready_events(
    netsapiens_call_subscription_id: str,
    practice_id: str,
    voip_provider_id: str,
    events: List[Dict],
    topic_path_leg_b_finished: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> List[pubsub_v1.publisher.futures.Future]:

    publish_futures = []
    cdrs_published = []  # for logging

    for event in events:
        # One of the leg-b's is finished only when these requirements are true,
        # otherwise the leg-b is still on-going and hasn't been finished yet.

        publish_future = publish_leg_b_ready_event(
            netsapiens_call_subscription_id=netsapiens_call_subscription_id,
            practice_id=practice_id,
            voip_provider_id=voip_provider_id,
            event=event,
            topic_path_leg_b_finished=topic_path_leg_b_finished,
            publisher=publisher,
        )
        if not publish_future:
            continue

        publish_futures.append(publish_future)
        cdrs_published.append(event)

    log.info(f"Published messages {cdrs_published} with error handler to {topic_path_leg_b_finished}. Only fully finished leg b CDRs")
    return publish_futures


def publish_leg_b_ready_event(
    netsapiens_call_subscription_id: str,
    practice_id: str,
    voip_provider_id: str,
    event: Dict,
    topic_path_leg_b_finished: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    if not (event.get("remove") == "yes" and event.get("term_leg_tag")):
        return None

    event_attributes = {
        "netsapiens_call_subscription_id": netsapiens_call_subscription_id,
        "practice_id": practice_id,
        "voip_provider_id": voip_provider_id,
    }
    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_leg_b_finished, publisher=publisher)


def publish_netsapiens_cdr_saved_event(
    practice_id: str,
    event: Dict,
    topic_path_netsapiens_cdr_saved: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_CDR_SAVED,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    event_attributes = {"practice_id": practice_id}
    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_netsapiens_cdr_saved, publisher=publisher)


def publish_netsapiens_cdr_linked_to_call_partial_event(
    practice_id: str,
    voip_provicer_id: str,
    event: Dict,
    topic_path_netsapiens_cdr_linked_to_call_partial: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_CDR_LINKED_TO_CALL_PARTIAL,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    description_human_readable = """Event indicates the following are true: 1. peerlogic call exist (call was created, call was updated) # 2. peerlogic call partial exists (partial was created, partial was updated) # 3. cdr2 has been linked to call and call partial # 4. netsapiens audio is available to download"""
    event_attributes = {
        "practice_id": practice_id,
        "voip_provider_id": voip_provicer_id,
        "description_human_readable": description_human_readable,
    }

    # modify the event to fulfill downstream contract
    event = {
        "peerlogic_call_id": event["peerlogic_call_id"],
        "peerlogic_call_partial_id": event["peerlogic_call_partial_id"],
        "netsapiens_orig_callid": event["cdrr_orig_callid"],
        "netsapiens_term_callid": event["cdrr_term_callid"],
    }

    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_netsapiens_cdr_linked_to_call_partial, publisher=publisher)


def publish_event(
    event_attributes: Dict,
    event: Dict,
    topic_path: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    event_encoded_data = json.dumps(event, default=json_serializer).encode("utf-8")

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event_encoded_data} with error handler to {topic_path}.")
    publish_future = publisher.publish(topic=topic_path, data=event_encoded_data, **event_attributes)
    log.info(f"Published message {event_encoded_data} with error handler to {topic_path}.")

    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, event_encoded_data))
