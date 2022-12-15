import base64
import json
import logging
from typing import Dict

log = logging.getLogger(__name__)


def foo(event: Dict, context: Dict) -> None:
    """
    Background Cloud Function to be triggered by Pub/Sub.
    """

    log.info(f"Started foo! Event: {event}, Context: {context}")
    data = base64.b64decode(event["data"]).decode("utf-8")

    # validate and get event data
    log.info(f"Validating attributes and decoded data: '{data}'")

    data = json.loads(data)
    log.info(f"Data: {data}")
    log.info(f"Completed foo!")
