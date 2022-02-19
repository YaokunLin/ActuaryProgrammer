import json
import logging

from django.conf import settings
from google.cloud import pubsub_v1

from core import pubsub_helpers


# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_call_audio_saved(
    call_id: str,
    call_audio_id: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_call_audio_saved: str = settings.PUBSUB_TOPIC_PATH_CALL_AUDIO_SAVED,
):
    event_data = {"call_id": call_id, "call_audio_id": call_audio_id}

    call_audio_saved_encode_data = json.dumps(event_data).encode("utf-8")
    event_attributes = {"call_id": call_id}

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event_data} with error handler to {topic_path_call_audio_saved}.")
    publish_future = publisher.publish(topic=topic_path_call_audio_saved, data=call_audio_saved_encode_data, **event_attributes)
    log.info(f"Published message {event_data} with error handler to {topic_path_call_audio_saved}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, call_audio_saved_encode_data))

    return publish_future


def publish_call_audio_partial_saved(
    call_id: str,
    partial_id: str,
    audio_partial_id: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_call_audio_partial_saved: str = settings.PUBSUB_TOPIC_PATH_CALL_AUDIO_PARTIAL_SAVED,
):
    event_data = {"call_id": call_id, "partial_id": partial_id, "audio_partial_id": audio_partial_id}

    call_audio_partial_encode_data = json.dumps(event_data).encode("utf-8")
    event_attributes = {"call_id": call_id}

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event_data} with error handler to {topic_path_call_audio_partial_saved}.")
    publish_future = publisher.publish(topic=topic_path_call_audio_partial_saved, data=call_audio_partial_encode_data, **event_attributes)
    log.info(f"Published message {event_data} with error handler to {topic_path_call_audio_partial_saved}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, call_audio_partial_encode_data))

    return publish_future


def publish_call_transcript_saved(
    call_id: str,
    call_transcript_id: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_call_transcript_saved: str = settings.PUBSUB_TOPIC_PATH_CALL_TRANSCRIPT_SAVED,
):
    event_data = {"call_id": call_id, "call_transcript_id": call_transcript_id}

    call_transcript_encode_data = json.dumps(event_data).encode("utf-8")
    event_attributes = {"call_id": call_id}

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event_data} with error handler to {topic_path_call_transcript_saved}.")
    publish_future = publisher.publish(topic=topic_path_call_transcript_saved, data=call_transcript_encode_data, **event_attributes)
    log.info(f"Published message {event_data} with error handler to {topic_path_call_transcript_saved}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, call_transcript_encode_data))

    return publish_future
