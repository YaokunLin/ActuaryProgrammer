import logging
from typing import Dict, List

from django.conf import settings
from google.cloud import pubsub_v1

from core.pubsub_helpers import publish_event

# Get an instance of a logger
log = logging.getLogger(__name__)


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

    if event.get("remove") != "yes":
        log.info(f"Detected leg b ready event that will be ignored instead of published. event: '{event}'")
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
    voip_provider_id: str,
    call_connection: str,
    went_to_voicemail: str,
    event: Dict,
    topic_path_netsapiens_cdr_linked_to_call_partial: str = settings.PUBSUB_TOPIC_PATH_NETSAPIENS_CDR_LINKED_TO_CALL_PARTIAL,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    description_human_readable = """Event indicates the following are true: 1. peerlogic call exist (call was created, call was updated) # 2. peerlogic call partial exists (partial was created, partial was updated) # 3. cdr2 has been linked to call and call partial # 4. netsapiens audio is available to download"""

    event_attributes = {
        "practice_id": practice_id,
        "voip_provider_id": voip_provider_id,
        "call_connection": call_connection,
        "went_to_voicemail": str(went_to_voicemail),  # All attributes being published to Pub/Sub must be sent as text strings.
        "description_human_readable": description_human_readable,
    }

    # modify the event to fulfill downstream contract
    event = {
        "cdr2_extract_id": event["id"],
        "peerlogic_call_id": event["peerlogic_call_id"],
        "peerlogic_call_partial_id": event["peerlogic_call_partial_id"],
        "netsapiens_orig_callid": event["cdrr_orig_callid"],
        "netsapiens_term_callid": event["cdrr_term_callid"],
    }

    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_netsapiens_cdr_linked_to_call_partial, publisher=publisher)
