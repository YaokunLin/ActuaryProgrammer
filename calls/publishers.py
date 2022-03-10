import logging

from django.conf import settings


from core.pubsub_helpers import publish_event


# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_call_audio_saved(
    call_id: str,
    call_audio_id: str,
    topic_path_call_audio_saved: str = settings.PUBSUB_TOPIC_PATH_CALL_AUDIO_SAVED,
):
    event_data = {"call_id": call_id, "call_audio_id": call_audio_id}
    event_data.update(settings.ML_PROCESS_ARGUMENTS)
    event_attributes = {"call_id": call_id}
    return publish_event(event_attributes=event_attributes, event=event_data, topic_path=topic_path_call_audio_saved)


def publish_call_audio_partial_saved(
    call_id: str,
    partial_id: str,
    audio_partial_id: str,
    topic_path_call_audio_partial_saved: str = settings.PUBSUB_TOPIC_PATH_CALL_AUDIO_PARTIAL_SAVED,
):
    event_data = {"call_id": call_id, "partial_id": partial_id, "audio_partial_id": audio_partial_id}
    event_attributes = {"call_id": call_id}

    return publish_event(event_attributes=event_attributes, event=event_data, topic_path=topic_path_call_audio_partial_saved)


def publish_call_transcript_saved(
    call_id: str,
    call_transcript_id: str,
    topic_path_call_transcript_saved: str = settings.PUBSUB_TOPIC_PATH_CALL_TRANSCRIPT_SAVED,
):
    event_data = {"call_id": call_id, "call_transcript_id": call_transcript_id}
    event_attributes = {"call_id": call_id}
    return publish_event(event_attributes=event_attributes, event=event_data, topic_path=topic_path_call_transcript_saved)
