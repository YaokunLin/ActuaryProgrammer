import json
import logging
from concurrent import futures
from datetime import date, datetime, timedelta
from typing import Callable, Dict

from django.conf import settings
from django.db import models
from google.cloud import pubsub_v1

# Get an instance of a logger
log = logging.getLogger(__name__)


def get_callback(publish_future: pubsub_v1.publisher.futures.Future, data: str) -> Callable[[pubsub_v1.publisher.futures.Future], None]:
    def callback(publish_future: pubsub_v1.publisher.futures.Future) -> None:
        try:
            # Wait x seconds for the publish call to succeed.
            log.info(publish_future.result(timeout=settings.PUBLISH_FUTURE_TIMEOUT_IN_SECONDS))
        except futures.TimeoutError:
            log.info(f"Publishing {data} timed out.")

    return callback


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)
    if isinstance(obj, models.Model):
        return obj.id

    raise TypeError(f"Type {type(obj)} not serializable")


def publish_event(
    event_attributes: Dict,
    event: Dict,
    topic_path: str,
    publisher: pubsub_v1.PublisherClient = settings.PUBLISHER,
) -> pubsub_v1.publisher.futures.Future:

    event_encoded_data = json.dumps(event, default=json_serializer).encode("utf-8")

    # When you publish a message, the client returns a future.
    log.info(f"Publishing message bytes {event_encoded_data} with error handler to {topic_path}.")
    publish_future = publisher.publish(topic=topic_path, data=event_encoded_data, **event_attributes)
    log.info(f"Published message bytes {event_encoded_data} with error handler to {topic_path}.")

    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(get_callback(publish_future, event_encoded_data))

    return publish_future
