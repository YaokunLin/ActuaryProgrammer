import io
import logging
import os
from datetime import datetime
from typing import Callable, Dict, List

import requests
import requests.compat
from pydantic import parse_obj_as
from urllib3.response import HTTPResponse

from devtools.api_clients.api_client import (
    APIClient,
    APIClientAuthenticationError,
    extract_and_transform,
    requires_auth,
)
from devtools.api_clients.models.peerlogic_api_models import (
    AgentEngagedWith,
    CallOutcome,
    CallOutcomeReason,
    CallPurpose,
    CallTranscript,
    NetsapiensAPICredentials,
    TelecomCallerNameInfo,
)
from devtools.api_clients.netsapiens_api_client import (
    NetsapiensAuthToken,
    NetsapiensRefreshToken,
)

log = logging.getLogger(__name__)


def transform_to_bytes(response: requests.Response) -> bytes:
    return response.content


def transform_to_call_transcript(response: requests.Response) -> List[CallTranscript]:
    data = response.json()
    transcript_count = data.get("count")
    transcript_list = data.get("results")

    return parse_obj_as(List[CallTranscript], transcript_list)


def transform_to_agent_engaged_with(response: requests.Response) -> AgentEngagedWith:
    return AgentEngagedWith(**response.json())


def transform_to_call_outcome(response: requests.Response) -> CallOutcome:
    return CallOutcome(**response.json())


def transform_to_call_outcome_reason(response: requests.Response) -> CallOutcomeReason:
    return CallOutcomeReason(**response.json())


def transform_to_call_purpose(response: requests.Response) -> CallPurpose:
    return CallPurpose(**response.json())


def transform_to_netsapiens_api_credentials(response: requests.Response) -> NetsapiensAPICredentials:
    data = response.json()
    credentials_count = data.get("count")
    credentials_list = data.get("results")
    if credentials_count == 0:
        raise Exception(f"No active credentials found from url='{response.request.url}'")

    return NetsapiensAPICredentials(**credentials_list[0])


def transform_to_telecom_caller_name_info(response: requests.Response) -> TelecomCallerNameInfo:
    return TelecomCallerNameInfo(**response.json())


class PeerlogicAPIClient(APIClient):
    def __init__(self, peerlogic_api_url: str = None, username: str = None, password: str = None) -> None:
        # fallback to well-known environment variables
        if not peerlogic_api_url:
            peerlogic_api_url = os.getenv("PEERLOGIC_API_URL")

        super().__init__(peerlogic_api_url)

        # fallback to well-known environment variables
        if not username:
            self._username = os.getenv("PEERLOGIC_API_USERNAME")

        if not password:
            self._password = os.getenv("PEERLOGIC_API_PASSWORD")

        # create base urls
        root_api_url = self.root_api_url
        self._peerlogic_auth_url = requests.compat.urljoin(root_api_url, "login")
        self._peerlogic_calls_url = requests.compat.urljoin(root_api_url, "calls/")
        self._peerlogic_netsapiens_api_credentials_url = requests.compat.urljoin(root_api_url, "integrations/netsapiens/admin/api-credentials")
        self._peerlogic_api_telecom_caller_name_info_url = requests.compat.urljoin(root_api_url, "/api/telecom-caller-name-info/")

    #
    # URL creators
    #

    def get_auth_url(self) -> str:
        return self._peerlogic_auth_url

    def get_netsapiens_api_credentials_url(self) -> str:
        return self._peerlogic_netsapiens_api_credentials_url

    def get_call_url(self, call_id: str = "") -> str:
        """Returns url for a particular resource if call id is given, otherwise gives list/create endpoint"""
        if call_id:
            call_id = f"{call_id}/"  # patches need trailing slashes
        return requests.compat.urljoin(self._peerlogic_calls_url, call_id)

    def get_call_partials_url(self, call_id: str = "") -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "partials/")

    def get_agent_engaged_with_url(self, call_id: str = "") -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "agent-engaged-with/")

    def get_call_purposes_url(self, call_id: str = "") -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "purposes/")

    def get_call_outcomes_url(self, call_id: str = "") -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "outcomes/")

    def get_call_outcome_reasons_url(self, call_id: str = "") -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "outcome-reasons/")

    def get_call_procedure_mentioned_url(self, call_id: str = "") -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "mentioned-procedures/")

    def get_call_audio_url(self, call_id, call_audio_id: str = None) -> str:
        """Returns url for a particular resource if call id is given, otherwise gives list/create endpoint"""
        if call_audio_id:  # url is for a particular resource
            return requests.compat.urljoin(self.get_call_url(call_id), f"audio/{call_audio_id}/")
        return requests.compat.urljoin(self.get_call_url(call_id), f"audio/")

    def get_call_partial_url(self, call_id: str, call_partial_id: str = None) -> str:
        """Returns url for a particular resource if call partial id is given, otherwise gives list/create endpoint"""
        if call_partial_id:  # url is for a particular resource
            return requests.compat.urljoin(self.root_api_url, f"/api/calls/{call_id}/partials/{call_partial_id}/")
        return requests.compat.urljoin(self.root_api_url, f"/api/calls/{call_id}/partials/")

    def get_call_audio_partial_url(self, call_id: str, call_partial_id: str, call_audio_partial_id: str = None) -> str:
        """Returns url for a particular resource if call audio partial id is given, otherwise gives list/create endpoint"""
        if call_audio_partial_id:  # url is for a particular resource
            return requests.compat.urljoin(self.root_api_url, f"/api/calls/{call_id}/partials/{call_partial_id}/audio/{call_audio_partial_id}/")
        return requests.compat.urljoin(self.root_api_url, f"/api/calls/{call_id}/partials/{call_partial_id}/audio/")

    def get_call_audio_partial_publish_url(self, call_id: str, call_partial_id: str, call_audio_partial_id: str) -> str:
        """Returns url for a particular resource if call audio partial id is given, otherwise gives list/create endpoint"""
        return requests.compat.urljoin(
            self.root_api_url, f"/api/calls/{call_id}/partials/{call_partial_id}/audio/{call_audio_partial_id}/publish_call_audio_partial_saved/"
        )

    def get_call_audio_partial_file_patch_url(self, call_id: str, call_partial_id: str, call_audio_partial_id: str = None) -> str:
        return requests.compat.urljoin(self.get_call_audio_partial_url(call_id, call_partial_id, call_audio_partial_id), "upload_file/")

    def get_call_transcripts_url(self, call_id: str) -> str:
        call_url = self.get_call_url(call_id)
        return requests.compat.urljoin(call_url, "transcripts/")

    def get_call_transcript_partial_url(self, call_id: str, call_partial_id: str, call_transcript_partial_id: str = "") -> str:
        """Returns url for a particular resource if call audio partial id is given, otherwise gives list/create endpoint"""
        if call_transcript_partial_id:  # url is for a particular resource
            call_transcript_partial_id = f"{call_transcript_partial_id}/"  # patches need trailing slashes
        return requests.compat.urljoin(self.get_call_partial_url(call_id, call_partial_id), f"transcripts/{call_transcript_partial_id}")

    def get_netsapiens_api_credentials_url(self) -> str:
        return self._peerlogic_netsapiens_api_credentials_url

    #
    # Login and session handling
    #

    def get_session(self) -> requests.Session:
        s = self._session
        if not s:
            raise APIClientAuthenticationError("Session is None. Must call the login() method before calling any other api accessor.")

        return s

    def login(self, username: str = None, password: str = None, request: Callable = requests.request) -> requests.Response:
        """Perform a login, grabbing an auth token."""
        try:
            # allow one-time overrides when calling login
            if username is None:
                username = self._username

            if password is None:
                password = self._password

            response = None  # define for proper logging as needed

            headers = {"Content-Type": "application/x-www-form-urlencoded"}  # explicitly set even though it's not necessary
            payload = {"username": username, "password": password}

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
            if response is not None and response.text:
                msg = f"{msg}. Response text: '{response.text}'"
            raise Exception(msg) from e

    def refresh_token(self, refresh_token: str = None, request: Callable = requests.request) -> requests.Response:
        try:
            if refresh_token is None:
                refresh_token = self._auth_token.refresh_token

            response = None  # define for proper logging as needed

            headers = {"Content-Type": "application/x-www-form-urlencoded"}  # explicitly set even though it's not necessary
            payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}

            url = self.get_auth_url()
            log.info(f"Re-authing into url='{url}'")
            auth_response = request("POST", url, headers=headers, data=payload)
            auth_response.raise_for_status()

            # parse response
            self._auth_token = NetsapiensRefreshToken.parse_obj(auth_response.json())  # be aware this is different, should we merge the dicts?

            # Session and Authorization header construction
            access_token = self._auth_token.access_token
            self._session = requests.Session()
            self._session.headers.update({"Authorization": f"Bearer {access_token}"})

            return auth_response
        except Exception as e:
            msg = f"Problem occurred authenticating to url '{url}'."
            if response is not None and response.text:
                msg = f"{msg}. Response text: '{response.text}'"
            raise Exception(msg) from e

    # TODO: Remove - just for testing logging of response text for 400s
    @requires_auth
    def create_foo_barred_procedure_mentioned(self, call_id: str, keyword: str, session: requests.Session = None) -> requests.Response:
        url = self.get_call_procedure_mentioned_url(call_id=call_id)

        if not session:
            session = self.get_session()

        procedure_mentioned_data = {
            "foo": "bar",
        }
        response = session.post(url=url, data=procedure_mentioned_data)
        return response

    @extract_and_transform(transform_to_netsapiens_api_credentials)
    @requires_auth
    def get_netsapiens_api_credentials(self, voip_provider_id: str, session: requests.Session = None) -> requests.Response:
        """
        Perform a login, grabbing an auth token.
        This works for both Netsapiens and peerlogic.
        """
        url = self.get_netsapiens_api_credentials_url()
        log.info(f"Retrieving netsapiens_api_credentials for voip_provider_id='{voip_provider_id}' from url='{url}'")

        if not session:
            session = self.get_session()

        response = session.get(url, params={"voip_provider_id": voip_provider_id, "active": True})
        return response

    @requires_auth
    def initialize_call_partial(
        self, call_id: str, time_interaction_started: datetime, time_interaction_ended: datetime, session: requests.Session = None
    ) -> requests.Response:
        url = self.get_call_partial_url(call_id)
        data = {"call": call_id, "time_interaction_started": time_interaction_started, "time_interaction_ended": time_interaction_ended}

        if not session:
            session = self.get_session()

        response = session.post(url=url, data=data)
        return response

    @requires_auth
    def get_call_audio_partial_list(self, call_id: str, call_partial_id: str, session: requests.Session = None) -> requests.Response:
        url = self.get_call_audio_partial_url(call_id, call_partial_id)

        if not session:
            session = self.get_session()

        response = session.get(url=url)
        return response

    @requires_auth
    def get_call_audio_partial(self, call_id: str, call_partial_id: str, call_audio_partial_id: str, session: requests.Session = None) -> requests.Response:
        url = self.get_call_audio_partial_url(call_id, call_partial_id, call_audio_partial_id)

        if not session:
            session = self.get_session()

        response = session.get(url=url)
        return response

    @extract_and_transform(transform_to_bytes)
    @requires_auth
    def get_call_audio_partial_wav_file(
        self, call_id: str, call_partial_id: str, call_audio_partial_id: str, session: requests.Session = None
    ) -> requests.Response:
        call_audio_data: requests.Response = self.get_call_audio_partial(call_id, call_partial_id, call_audio_partial_id)
        url: str = call_audio_data.json().get("signed_url")

        if not session:
            session = self.get_session()
        response = session.get(url=url)

        return response

    @requires_auth
    def initialize_call_audio_partial(self, call_id, call_partial_id, mime_type="audio/WAV", session: requests.Session = None) -> requests.Response:
        url = self.get_call_audio_partial_url(call_id, call_partial_id)
        data = {"mime_type": mime_type, "call_partial": call_partial_id}

        if not session:
            session = self.get_session()

        response = session.post(url=url, data=data)
        return response

    @requires_auth
    def patch_call_audio_partial(
        self, call_id, call_partial_id, call_audio_partial_id: str, changes: Dict, session: requests.Session = None
    ) -> requests.Response:
        url = self.get_call_audio_partial_url(call_id, call_partial_id, call_audio_partial_id)
        data = changes

        if not session:
            session = self.get_session()

        response = session.patch(url=url, data=data)
        return response

    @requires_auth
    def finalize_call_audio_partial(
        self, call_id: str, call_partial_id: str, call_audio_partial_id, file: HTTPResponse, mime_type: str = "audio/WAV", session: requests.Session = None
    ) -> requests.Response:
        url = self.get_call_audio_partial_file_patch_url(call_id, call_partial_id, call_audio_partial_id)
        files = {mime_type: file}

        if not session:
            session = self.get_session()

        response = session.patch(url=url, files=files)
        return response

    @requires_auth
    def get_call_detail(self, call_id: str, session: requests.Session = None) -> requests.Response:
        url = self.get_call_url(call_id)

        if not session:
            session = self.get_session()

        response = session.get(url=url)
        return response

    @requires_auth
    def get_call_audio(self, call_id: str, call_audio_id: str, session: requests.Session = None) -> requests.Response:
        url = self.get_call_audio_url(call_id, call_audio_id)

        if not session:
            session = self.get_session()

        response = session.get(url=url)
        return response

    @requires_auth
    def get_call_audio_wave_file(self, call_id: str, call_audio_id: str, session: requests.Session = None) -> requests.Response:
        call_audio_data = self.get_call_audio(call_id, call_audio_id).json()
        url: str = call_audio_data.get("signed_url")

        if not session:
            session = self.get_session()

        response = session.get(url=url)
        return response

    @extract_and_transform(transform_to_telecom_caller_name_info)
    @requires_auth
    def get_telecom_caller_name_info(self, phone_number: str, session: requests.Session = None) -> requests.Response:
        # generate call with phone_number appended
        url = requests.compat.urljoin(self._peerlogic_api_telecom_caller_name_info_url, phone_number)

        if not session:
            session = self.get_session()

        response = session.get(url=url)
        return response

    @extract_and_transform(transform_to_call_purpose)
    @requires_auth
    def create_call_purpose(self, call_purpose: CallPurpose, session: requests.Session = None) -> requests.Response:
        call_id = call_purpose.call
        url = self.get_call_purposes_url(call_id=call_id)

        if not session:
            session = self.get_session()

        response = session.post(url=url, data=call_purpose.dict())
        return response

    @extract_and_transform(transform_to_agent_engaged_with)
    @requires_auth
    def create_agent_engaged_with(self, agent_engaged_with: AgentEngagedWith, session: requests.Session = None) -> requests.Response:
        call_id = agent_engaged_with.call
        url = self.get_agent_engaged_with_url(call_id=call_id)

        if not session:
            session = self.get_session()

        response = session.post(url=url, data=agent_engaged_with.dict())
        return response

    @extract_and_transform(transform_to_call_outcome)
    @requires_auth
    def create_call_outcome(self, call_id: str, call_outcome: CallOutcome, session: requests.Session = None) -> requests.Response:
        url = self.get_call_outcomes_url(call_id=call_id)

        if not session:
            session = self.get_session()

        response = session.post(url=url, data=call_outcome.dict())
        return response

    @extract_and_transform(transform_to_call_outcome_reason)
    @requires_auth
    def create_call_outcome_reason(self, call_id: str, call_outcome_reason: CallOutcomeReason, session: requests.Session = None) -> requests.Response:
        url = self.get_call_outcome_reasons_url(call_id=call_id)

        if not session:
            session = self.get_session()

        response = session.post(url=url, data=call_outcome_reason.dict())
        return response

    @requires_auth
    def republish_call_audio_partial(
        self, call_id: str, call_partial_id: str, call_audio_partial_id: str, session: requests.Session = None
    ) -> requests.Response:
        url = self.get_call_audio_partial_publish_url(call_id=call_id, call_partial_id=call_partial_id, call_audio_partial_id=call_audio_partial_id)

        if not session:
            session = self.get_session()

        response = session.post(url=url)
        return response

    @requires_auth
    def create_procedure_mentioned(self, call_id: str, keyword: str, session: requests.Session = None) -> requests.Response:
        url = self.get_call_procedure_mentioned_url(call_id=call_id)

        if not session:
            session = self.get_session()

        procedure_mentioned_data = {
            "call": call_id,
            "keyword": keyword,
        }
        response = session.post(url=url, data=procedure_mentioned_data)
        return response

    @extract_and_transform(transform_to_call_transcript)
    @requires_auth
    def get_transcripts_for_call(self, call_id: str, filter_params: Dict = None, session: requests.Session = None) -> requests.Response:
        url = self.get_call_transcripts_url(call_id=call_id)

        if not session:
            session = self.get_session()

        if not filter_params:
            filter_params = {}

        response = session.get(url=url, params=filter_params)
        return response

    def get_transcripts_with_text_for_call(self, call_id: str, filter_params: Dict = None, session: requests.Session = None) -> List[CallTranscript]:
        transcripts: List[CallTranscript] = self.get_transcripts_for_call(call_id=call_id, filter_params=filter_params, session=session)

        if not session:
            session = self.get_session()

        for transcript in transcripts:
            signed_url = transcript.signed_url
            text = session.get(signed_url).text
            transcript.text = text

        return transcripts

    @requires_auth
    def initialize_call_transcript_partial(
        self, call_id: str, call_partial_id: str, transcript_type: str, mime_type: str = "text/plain", session: requests.Session = None
    ) -> requests.Response:

        if not session:
            session = self.get_session()

        url = self.get_call_transcript_partial_url(call_id, call_partial_id)
        data = {"mime_type": mime_type, "call_partial": call_partial_id, "transcript_type": transcript_type}

        response = session.post(url=url, data=data)
        return response

    @requires_auth
    def finalize_call_transcript_partial(
        self,
        id: str,
        call_id: str,
        call_partial_id: str,
        transcript_string: str,
        mime_type: str = "text/plain",
        session: requests.Session = None,
    ) -> requests.Response:

        if not session:
            session = self.get_session()

        url = self.get_call_transcript_partial_url(call_id, call_partial_id, id)
        file = io.StringIO(transcript_string)
        files = {mime_type: file}

        response = session.patch(url=url, files=files)
        return response


#
# Entrypoint
#

if __name__ == "__main__":
    """Only run when from command line / scripted."""
    # ensure environment variables are loaded
    from dotenv import load_dotenv

    load_dotenv()

    # create client and login
    peerlogic_api = PeerlogicAPIClient()
    call_id = "DSCJj2V3KAGeVhVow3C9yd"
    call_purpose: CallPurpose = peerlogic_api.create_call_purpose(
        call_purpose=CallPurpose(call=call_id, call_purpose_type="billing", raw_call_purpose_model_run_id="blah")
    )
    print(call_purpose)
    call_outcome = peerlogic_api.create_call_outcome(
        call_id=call_id, call_outcome=CallOutcome(call_purpose=call_purpose.id, call_outcome_type="failure", raw_call_outcome_model_run_id="blah2")
    )
    print(call_outcome)
    call_outcome_reason = peerlogic_api.create_call_outcome_reason(
        call_id=call_id,
        call_outcome_reason=CallOutcomeReason(
            call_outcome=call_outcome.id, call_outcome_reason_type="call_interrupted", raw_call_outcome_reason_model_run_id="ladhfa"
        ),
    )
    print(call_outcome_reason)

    call_procedure_mentioned = peerlogic_api.create_procedure_mentioned(call_id=call_id, keyword="exam")
    print(call_procedure_mentioned.json())

    peerlogic_api.login()
    log.info(peerlogic_api._auth_token.access_token)

    # test format with non alpha characters
    caller_name_info = peerlogic_api.get_telecom_caller_name_info("1 (800) 554-1907")  # delta dental
    print(caller_name_info)
    print(caller_name_info.is_business())
    print(caller_name_info.is_consumer_carrier_type())

    # test expected e164 format
    caller_name_info = peerlogic_api.get_telecom_caller_name_info("+18005541907")  # delta dental
    print(caller_name_info)
    print(caller_name_info.is_business())
    print(caller_name_info.is_consumer_carrier_type())

    caller_name_info = peerlogic_api.get_telecom_caller_name_info("8005541907")  # delta dental
    print(caller_name_info)
    print(caller_name_info.is_business())
    print(caller_name_info.is_consumer_carrier_type())
