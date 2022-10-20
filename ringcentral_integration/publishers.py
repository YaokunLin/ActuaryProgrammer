import logging

from django.conf import settings
from google.cloud import pubsub_v1

from core.pubsub_helpers import publish_event

# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_call_create_call_record_event(
    practice_id: str,
    voip_provider_id: str,
    ringcentral_telephony_session_id: str,
    ringcentral_session_id: str,
    topic_path_ringcentral_call_disconnected: str = settings.PUBSUB_TOPIC_ID_RINGCENTRAL_CALL_DISCONNECTED,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
):

    event_attributes = {
        "practice_id": practice_id,
        "voip_provider_id": voip_provider_id,
    }

    event = {
        "ringcentral_telephony_session_id": ringcentral_telephony_session_id,
        "ringcentral_session_id": ringcentral_session_id,
    }

    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_ringcentral_call_disconnected, publisher=publisher)


def publish_ringcentral_create_call_audio_event(
    practice_id: str,
    voip_provider_id: str,
    peerlogic_call_id: str,
    peerlogic_call_partial_id: str,
    ringcentral_recording_id: str,
    topic_path_ringcentral_get_call_audio: str = settings.PUBSUB_TOPIC_PATH_RINGCENTRAL_GET_CALL_AUDIO,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    event_attributes = {
        "practice_id": practice_id,
        "voip_provider_id": voip_provider_id,
    }

    # modify the event to fulfill downstream contract
    event = {
        "peerlogic_call_id": peerlogic_call_id,
        "peerlogic_call_partial_id": peerlogic_call_partial_id,
        "ringcentral_recording_id": ringcentral_recording_id,
    }

    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_ringcentral_get_call_audio, publisher=publisher)
