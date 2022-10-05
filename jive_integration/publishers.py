import logging
from typing import Dict, List

from django.conf import settings
from google.cloud import pubsub_v1

from core.pubsub_helpers import publish_event

# Get an instance of a logger
log = logging.getLogger(__name__)


def publish_leg_b_ready_event(
    jive_call_subscription_id: str,
    voip_provider_id: str,
    event: Dict,
    topic_path_leg_b_finished: str = settings.PUBSUB_TOPIC_PATH_JIVE_LEG_B_FINISHED,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    event_attributes = {
        "jive_call_subscription_id": jive_call_subscription_id,
        "voip_provider_id": voip_provider_id,
    }
    return publish_event(event_attributes=event_attributes, event=event, topic_path=topic_path_leg_b_finished, publisher=publisher)
