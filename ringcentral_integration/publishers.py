import logging
from django.conf import settings
from google.cloud import pubsub_v1

from core.pubsub_helpers import publish_event


# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_call_discounted_event(
    ringcentral_telephony_session_id: str,
    practice_id: str,
    ringcentral_account_id: str,
    topic_path_ringcentral_call_disconnected: str = settings.PUBSUB_TOPIC_PATH_RINGCENTRAL_CALL_DISCONNECTED,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
): 

    event_attributes = {
        "ringcentral_telephony_session_id": ringcentral_telephony_session_id,
        "practice_id": practice_id,
        "ringcentral_account_id": ringcentral_account_id,
    }

    return publish_event(event_attributes=event_attributes, event=[], topic_path=topic_path_ringcentral_call_disconnected, publisher=publisher)
