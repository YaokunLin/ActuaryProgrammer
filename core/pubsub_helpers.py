from concurrent import futures
import logging
from typing import Callable

from django.conf import settings

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
