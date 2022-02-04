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


def publish_call_transcript_partial_ready(
    call_id: str,
    transcript_type: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
    topic_path_transcript_partial_ready: str = settings.PUBSUB_TOPIC_PATH_TRANSCRIPT_PARTIAL_READY,
):

    log.info(f"Getting call for call_id {call_id}")
    call = Call.objects.get(pk=call_id)
    log.info(f"Got call for call_id {call_id}")

    log.info(f"Getting call partials for call_id {call_id}")
    call_partials = CallPartial.objects.filter(call=call_id).order_by("time_interaction_started")
    log.info(f"Got call partials for call_id {call_id}")

    call_transcript_partial_urls = []

    log.info(f"Getting {transcript_type} call transcript partial signed urls for call_id {call_id}")
    for call_partial in call_partials:
        call_transcript_partial_urls += [
            call_transcript_partial.signed_url
            for call_transcript_partial in CallTranscriptPartial.objects.filter(call_partial=call_partial, transcript_type=transcript_type)
        ]
        log.info(f"Got {transcript_type} call transcript partial signed urls for call_id {call_id}")

    partials = {"transcript_type": transcript_type, "call_transcript_partial_urls": call_transcript_partial_urls}

    call_transcript_partial_encode_data = json.dumps(partials, indent=2).encode("utf-8")
    event_attributes = {
        "call_id": call_id,
    }

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message {partials} with error handler to {topic_path_transcript_partial_ready}.")
    publish_future = publisher.publish(topic=topic_path_transcript_partial_ready, data=call_transcript_partial_encode_data, **event_attributes)
    log.info(f"Published message {partials} with error handler to {topic_path_transcript_partial_ready}.")
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, call_transcript_partial_encode_data))

    return publish_future
