from concurrent import futures
import json
import logging
from typing import Dict, List

from django.conf import settings
from google.cloud import pubsub_v1

from core import pubsub_helpers
from calls.field_choices import TranscriptTypes
from calls.models import Call, CallAudioPartial, CallPartial, CallTranscriptPartial


# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_call_audio_partial_ready(
    call_id: str,
    partial_id: str,
    audio_partial_id: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_audio_partial_ready: str = settings.PUBSUB_TOPIC_PATH_AUDIO_PARTIAL_READY,
):
    event_data = {"call_id": call_id, "partial_id": partial_id, "audio_partial_id": audio_partial_id}

    call_audio_partial_encode_data = json.dumps(event_data, indent=2).encode("utf-8")
    event_attributes = {"call_id": call_id}

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event_data} with error handler to {topic_path_audio_partial_ready}.")
    publish_future = publisher.publish(topic=topic_path_audio_partial_ready, data=call_audio_partial_encode_data, **event_attributes)
    log.info(f"Published message {event_data} with error handler to {topic_path_audio_partial_ready}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, call_audio_partial_encode_data))

    return publish_future


def publish_call_transcript_ready(
    call_id: str,
    call_transcript_id: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_call_transcript_ready: str = settings.PUBSUB_TOPIC_PATH_CALL_TRANSCRIPT_READY,
):
    event_data = {"call_id": call_id, "call_transcript_id": call_transcript_id}

    call_transcript_encode_data = json.dumps(event_data, indent=2).encode("utf-8")
    event_attributes = {"call_id": call_id}

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {event_data} with error handler to {topic_path_call_transcript_ready}.")
    publish_future = publisher.publish(topic=topic_path_call_transcript_ready, data=call_transcript_encode_data, **event_attributes)
    log.info(f"Published message {event_data} with error handler to {topic_path_call_transcript_ready}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, call_transcript_encode_data))

    return publish_future