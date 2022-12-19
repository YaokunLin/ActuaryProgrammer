import logging
from typing import Dict

from core.models import Practice
from peerlogic.decorators import try_catch_log

log = logging.getLogger(__name__)


@try_catch_log
def bar(event: Dict, context: Dict) -> None:
    """
    Background Cloud Function to be triggered by Pub/Sub.
    """

    log.info(f"Started bar! Event: {event}, Context: {context}")

    practices = Practice.objects.all()
    log.info(f"There are {len(practices)} practices and the DB totally works!")
    log.info(f"Completed bar!")
