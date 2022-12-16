# import base64
# import json
import logging
import traceback
from typing import Dict

from core.models import Practice

log = logging.getLogger(__name__)


def try_catch_log(wrapped_func):
    def wrapper(*args, **kwargs):
        try:
            response = wrapped_func(*args, **kwargs)
        except Exception as e:
            # Replace new lines with spaces to prevent several entries which would trigger several errors
            error_message = traceback.format_exc().replace("\n", "  ")
            log.critical(error_message)
            raise e
        return response

    return wrapper


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
