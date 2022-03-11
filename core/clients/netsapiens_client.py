from datetime import datetime
import logging
from typing import (
    Callable,
    Dict,
    List,
)
from urllib3.response import HTTPResponse

from pydantic import BaseModel, parse_obj_as
import requests
import requests.compat

from core.clients.api_client import APIClient


log = logging.getLogger(__name__)


class NetsapiensAuthToken(BaseModel):
    # Expected format as of 2022-02-22
    access_token: str  # alphanumberic
    apiversion: str  # e.g. "Version: 41.2.3"
    client_id: str  # peerlogic-api-ENVIRONMENT
    displayName: str  # USER NAME
    domain: str  # e.g. "Peerlogic"
    expires_in: int  # e.g. "3600"
    refresh_token: str  # alphanumberic
    scope: str  # e.g. "Super User"
    territory: str  # "Peerlogic"
    token_type: str  # "Bearer"
    uid: str  # e.g. "1234@Peerlogic"
    user: int  # e.g. "1234"
    user_email: str  # e.g. "r-and-d@peerlogic.com"
    username: str  # e.g. "1234@Peerlogic"


class NetsapiensRefreshToken(BaseModel):
    access_token: str  # alphanumberic
    apiversion: str  # e.g. "Version: 41.2.3"
    client_id: str  # peerlogic-api-ENVIRONMENT
    domain: str  # e.g. "Peerlogic"
    expires: int  # time when this token expires in seconds since epoch e.g. "1645728699"
    expires_in: int  # e.g. "3600"
    rate_limit: str  # e.g. "0", yes this is a string and not a number
    refresh_token: str  # alphanumberic
    scope: str  # e.g. "Super User"
    territory: str  # "Peerlogic"
    token_type: str  # "Bearer"
    uid: str  # e.g. "1234@Peerlogic"


class NetsapiensRecordingUrl(BaseModel):
    status: str  # unconverted, converted, archived
    call_id: str  # typically the orig_callid, also term_callid
    time_open: datetime
    time_close: datetime
    time: datetime
    duration: int  # in seconds
    url: str  # contains the recording
    geo_id: str  # na occurs when there isn't a geo
    size: int  # 0, 4096 may be the smallest we see


def transform_to_netsapiens_recording_urls(response: requests.Response) -> List[NetsapiensRecordingUrl]:
    # attempt to get response content as json
    try:
        recording_urls = response.json()
    except requests.exceptions.JSONDecodeError:
        msg = "Problem attempting to retrieve JSON response for recording urls. No JSON in response. No recording URLs found. It's expected that this may happen if a recording hasn't yet been generated."
        log.info(msg)
        raise Exception(msg)

    # detect typing and normalize to list
    if type(recording_urls) == dict:
        recording_urls = [recording_urls]
    recording_urls_count = len(recording_urls)

    # detect number of recording urls
    log.info(f"While transforming recording urls, detected a recording_urls_count='{recording_urls_count}'")
    if 0 == recording_urls_count:
        # it's not clear that this is possible, whether we can actually have an empty list here but we'll check anyway
        msg = f"Recieved {recording_urls_count} recording_urls, usually expecting 2 or more."
        raise Exception(msg)

    # convert and validate structure
    recording_urls = parse_obj_as(List[NetsapiensRecordingUrl], recording_urls)

    return recording_urls


def get_full_and_ready_netsapiens_recording_url(netsapiens_recording_urls: List[NetsapiensRecordingUrl]) -> NetsapiensRecordingUrl:
    # It is presumed that when we receive pairwise recordings, with at least 2
    # Hypothesis: it seems both recording pairs will contain the same content just recorded from opposite sender and recipient phone devices' rtp streams.
    # Data: When we listen to them, they seem to always sound the same.
    # There is probably much more to be gleaned here about left and right channels for PCMU (stereo) vs GSM (mono).
    # Sometimes, we get more recordings with subsequent recordings containing a subset of the recording audio.
    # We want the largest / longest
    try:
        full_recording_url = max(netsapiens_recording_urls, key=lambda recording: int(recording.duration))
        log.info(f"Found longest recording_url. full_recording_url='{full_recording_url}'")

        # check if converted / ready
        if full_recording_url.status == "unconverted":
            raise Exception(f"Full recording is not ready. Status in 'unconverted' full_recording_url'{full_recording_url}'")

        return full_recording_url
    except Exception as e:
        msg = f"Problem occurred getting the largest url from netsapiens_recording_urls='{netsapiens_recording_urls}'."
        raise Exception(msg) from e


class NetsapiensAPIClient(APIClient):
    def __init__(self, root_api_url: str) -> None:
        super().__init__(root_api_url=root_api_url)

        # create base urls
        root_api_url = self.root_api_url
        self._netsapiens_auth_url = requests.compat.urljoin(root_api_url, "oauth2/token/")

    def get_auth_url(self) -> str:
        return self._netsapiens_auth_url

    def get_session(self) -> requests.Session:
        s = self._session
        if not s:
            raise TypeError("Session is None. Must call the login() method before calling any other api accessor.")

        return s

    def login(self, username: str, password: str, client_id: str, client_secret: str, request: Callable = requests.request) -> requests.Response:
        """
        Perform a login, grabbing an auth token.
        """
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}  # explicitly set even though it's not necessary
            payload = {
                "username": username,
                "password": password,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "password",
                "format": "json",
            }

            url = self.get_auth_url()
            log.info(f"Authing into url='{url}' as username: '{username}'")
            auth_response = request("POST", url, headers=headers, data=payload)
            auth_response.raise_for_status()

            # parse response
            self._auth_token = NetsapiensAuthToken.parse_obj(auth_response.json())

            # Session and Authorization header construction
            access_token = self._auth_token.access_token
            self._session = requests.Session()
            self._session.headers.update({"Authorization": f"Bearer {access_token}"})

            return auth_response
        except Exception as e:
            msg = f"Problem occurred authenticating to url '{url}'."
            raise Exception(msg) from e

    def create_event_subscription(self, domain: str, post_url: str, session: requests.Session = None) -> HTTPResponse:
        try:
            response = None  # define for proper logging as needed
            if not session:
                session = self.get_session()

            data = {"object": "event", "action": "create", "domain": domain, "post_url": post_url, "expires": "2300-12-31", "model": "call", "format": "json"}
            url = self.root_api_url

            response = session.post(url=url, data=data)
            response.raise_for_status()

            log.info(f"Created event subscription response: '{response.text}'")
            return response
        except Exception as e:
            msg = f"Problem occurred creating event subscription from url='{url}', data='{data}'."
            if response is not None and response.text:
                msg = f"{msg}. Response text: '{response.text}'. Response code: '{response.status_code}'"
            raise Exception(msg) from e
