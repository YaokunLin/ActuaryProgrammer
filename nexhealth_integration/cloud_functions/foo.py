# import base64
# import json
import logging
from typing import Dict

from core.models import Practice
from peerlogic.decorators import try_catch_log

log = logging.getLogger(__name__)


@try_catch_log
def foo(event: Dict, context: Dict) -> None:
    """
    Background Cloud Function to be triggered by Pub/Sub.
    """

    log.info(f"Started foo! Event: {event}, Context: {context}")

    practices = Practice.objects.all()
    log.info(f"There are {len(practices)} practices and the DB totally works!")
    # data = base64.b64decode(event["data"]).decode("utf-8")
    #
    # # validate and get event data
    # log.info(f"Validating attributes and decoded data: '{data}'")
    #
    # data = json.loads(data)
    # log.info(f"Data: {data}")
    log.info(f"Completed foo!")
