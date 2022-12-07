import logging
import types
from functools import wraps
from typing import Callable, Dict

import requests
import requests.compat

log = logging.getLogger(__name__)


class APIClientAuthenticationError(Exception):
    pass


class APIClientAuthorizationError(Exception):
    pass


class APIClient(object):
    def __init__(self, root_api_url: str = None) -> None:
        self._session = None

        # normalize the base_url
        self.root_api_url = root_api_url
        log.debug(f"Initialized API Client. root_api_url: '{self._root_api_url}'")

    @property
    def root_api_url(self) -> str:
        return self._root_api_url

    @root_api_url.setter
    def root_api_url(self, value) -> None:
        self._root_api_url = value if value and value.endswith("/") else f"{value}/"

    def login(self) -> requests.Response:
        raise NotImplementedError()

    def refresh_token(self) -> requests.Response:
        raise NotImplementedError()


def requires_auth(func) -> Callable:
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> requests.Response:
        try:
            log.info("Invoking function requiring auth.")
            response: requests.Response = func(self, *args, **kwargs)  # attempt invocation
            log.info("Invoked function requiring auth. Performing raise for status check.")
            raise_for_bad_auth_and_other_statuses(response)
            log.info("Auth status is good. Returning value from function.")
            return response
        except APIClientAuthenticationError as e:
            log.info("Authentication Error. Not logged in. Attempting to login and retrying function.")
            self.login()
            return func(self, *args, **kwargs)  # re-attempt
        except APIClientAuthorizationError as e:
            log.info("Authorization Error. Token possibly expired. Attempting to refresh and retrying function.")
            self.refresh_token()
            return func(self, *args, **kwargs)  # re-attempt

    return wrapper


def extract_and_transform(translator: Callable) -> Callable:
    def decorator(function):
        def wrapper(*args, **kwargs):
            result = function(*args, **kwargs)
            return translator(result)

        return wrapper

    return decorator


def raise_for_bad_auth_and_other_statuses(response: requests.Response) -> requests.Response:
    status_code = response.status_code
    if 200 <= status_code <= 299:
        return status_code
    if status_code == 401:
        raise APIClientAuthenticationError()
    if status_code == 403:
        raise APIClientAuthorizationError()

    response.raise_for_status()
    return response  # shouldn't be possible, since raise_for_status should catch every other status code
