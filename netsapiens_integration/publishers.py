from datetime import (
    date,
    datetime,
    timedelta,
)
import json
import logging
from typing import Dict, List

from django.db import models
from django.conf import settings
from google.cloud import pubsub_v1

from core import pubsub_helpers
from netsapiens_integration.models import NetsapiensCallSubscriptionsEventExtract


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

    raise TypeError ("Type %s not serializable" % type(obj))


def publish_leg_b_ready_events(
    netsapiens_call_subscription_id: str,
    practice_id: str,
    voip_provider_id: str,
    events: List[Dict],
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_leg_b_finished: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED,
) -> List:

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
            publisher=publisher,
            topic_path_leg_b_finished=topic_path_leg_b_finished,
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
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_leg_b_finished: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED,
):
    if not (event.get("remove") == "yes" and event.get("term_leg_tag")):
        return None

    event_encoded_data = json.dumps(event).encode("utf-8")
    event_attributes = {
        "netsapiens_call_subscription_id": netsapiens_call_subscription_id,
        "practice_id": practice_id,
        "voip_provider_id": voip_provider_id,
    }

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event} with error handler to {topic_path_leg_b_finished}.")
    publish_future = publisher.publish(topic=topic_path_leg_b_finished, data=event_encoded_data, **event_attributes)
    log.info(f"Published message {event} with error handler to {topic_path_leg_b_finished}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, event_encoded_data))

    return publish_future


def publish_netsapiens_cdr_saved_event(
    practice_id: str,
    event: Dict,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_netsapiens_cdr_saved: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_CDR_SAVED,
):
    event_encoded_data = json.dumps(event, default=json_serializer).encode("utf-8")

    event_attributes = {"practice_id": practice_id}
    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event} with error handler to {topic_path_netsapiens_cdr_saved}.")
    publish_future = publisher.publish(topic=topic_path_netsapiens_cdr_saved, data=event_encoded_data, **event_attributes)
    log.info(f"Published message {event} with error handler to {topic_path_netsapiens_cdr_saved}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, event_encoded_data))

    return publish_future
