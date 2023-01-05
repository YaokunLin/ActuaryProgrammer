import logging
import traceback
from typing import Callable

log = logging.getLogger(__name__)


def try_catch_log(wrapped_func: Callable) -> Callable:
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
