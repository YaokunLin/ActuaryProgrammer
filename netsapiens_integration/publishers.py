from concurrent import futures
import json
from django.conf import settings
from typing import Dict, List

from core import pubsub_helpers


def publish_cdrs(event_data: List[Dict]):
    publish_futures = []

    for cdr in event_data:
        cdr_encode_data = json.dumps(cdr, indent=2).encode("utf-8")
        # When you publish a message, the client returns a future.
        publish_future = settings.PUBLISHER.publish(settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED, cdr_encode_data)
        # Non-blocking. Publish failures are handled in the callback function.
        publish_future.add_done_callback(pubsub_helpers.get_callback(publish_future, cdr_encode_data))
        publish_futures.append(publish_future)

    print(f"Published messages with error handler to {settings.PUBSUB_TOPIC_PATH_NETSAPIENS_LEG_B_FINISHED}.")
    return publish_futures
