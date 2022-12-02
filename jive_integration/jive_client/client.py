import hashlib
import json
import logging
import urllib.parse
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from django.utils import timezone
from requests.auth import AuthBase, HTTPBasicAuth
from core.field_choices import OAuthTokenTypes
from jive_integration.exceptions import RefreshTokenNoLongerRefreshableException
from rest_framework import status

from jive_integration.exceptions import RefreshTokenNoLongerRefreshableException
from jive_integration.models import (
    JiveAPICredentials,
    JiveChannel,
    JiveLine,
    JiveSession,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class Line:
    """
    Given lines are constantly being used to compare sets of data this abstraction allows us to easily compare them.
    """

    def __init__(self, line_id: str, source_organization_jive_id: str):
        self.line_id = line_id
        self.source_organization_jive_id = source_organization_jive_id

    def __hash__(self):
        return hash(self.line_id + self.source_organization_jive_id)

    def __eq__(self, other):
        return self.line_id == other.line_id and self.source_organization_jive_id == other.source_organization_jive_id


class APIResponseException(Exception):
    """
    Wraps any exception raised when parsing an API response.
    """

    pass


def safe_get_response_json(response):
    try:
        body = response.json()
    except json.decoder.JSONDecodeError:
        return None

    return body


class _Authentication(AuthBase):
    """
    https://developer.goto.com/guides/Authentication/05_HOW_refreshToken/

    The scenarios at the bottom of the page really illustrate why we have the daily "cron" to refresh credentials in bulk.
    """

    _authentication_url: str = "https://authentication.logmeininc.com"
    _goto_api_url: str = "https://api.getgo.com"

    _logging_prefix = {
        # TODO: OAuthCodeTypes.AUTHORIZATION_CODE: "",
        OAuthTokenTypes.ACCESS_TOKEN: "Successfully recieved first access_token",
        OAuthTokenTypes.REFRESH_TOKEN: "Successfully refreshed token",
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        jive_api_credentials: Optional[JiveAPICredentials] = None,
    ):
        if jive_api_credentials:
            self._access_token = jive_api_credentials.access_token
            self._access_token_expires_at = jive_api_credentials.access_token_expires_at
            self._refresh_token = jive_api_credentials.refresh_token
            self._scope = jive_api_credentials.scope
        else:
            self._access_token = access_token
            self._refresh_token = refresh_token

        self._client_id = client_id
        self._client_secret = client_secret
        self._account_key = None
        self._jive_api_credentials = jive_api_credentials

    def __call__(self, r: requests.Request):
        """
        Before sending the request check if the access token is present and not expired. If not, update the outgoing
        request with a valid access token header.
        """
        if not self._access_token or (self._access_token_expires_at and timezone.now() >= self._access_token_expires_at):
            log.info("Jive: Access token not present or expired, refreshing for a new access and refresh token.")
            self.refresh_for_new_token()
            log.info("Jive: Done refreshing token.")

        r.headers["Authorization"] = f"Bearer {self._access_token}"

        return r

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    def refresh_for_new_token(self):
        """
        Exchange the refresh token for a valid access token.

        https://developer.goto.com/guides/HowTos/05_HOW_refreshToken/
        """
        log.info(f"Jive: Refreshing for a new token for self._jive_api_credentials.id={self._jive_api_credentials.id}")

        request_body = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        log.debug(f"Jive: Refresh token request_body={request_body}, self._client_id='{self._client_id}', self._client_secret='{self._client_secret}'")
        response: requests.Response = requests.request(
            method="post",
            url=urllib.parse.urljoin(self._goto_api_url, "/oauth/v2/token"),
            auth=HTTPBasicAuth(self._client_id, self._client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=request_body,
        )

        self.__detect_bad_auth_response(response, OAuthTokenTypes.REFRESH_TOKEN)
        self.__parse_token_response(response=response, token_type=OAuthTokenTypes.REFRESH_TOKEN)

    def exchange_code(self, code: str, redirect_uri: str):
        """
        Exchange the given authorization code for a refresh and access token.

        https://developer.goto.com/Authentication/#section/Authorization-Flows/Authorization-Code-Grant

        Scroll to 2. Exchange the authorization code for an access token
        """

        response: requests.Response = requests.request(
            method="post",
            url=urllib.parse.urljoin(self._authentication_url, "/oauth/token"),
            auth=HTTPBasicAuth(self._client_id, self._client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "client_id": self._client_id},
        )

        self.__detect_bad_auth_response(response=response, token_type=OAuthTokenTypes.ACCESS_TOKEN)
        self.__parse_token_response(response=response, token_type=OAuthTokenTypes.ACCESS_TOKEN)

    def __detect_bad_auth_response(self, response: Optional[requests.Response], token_type: OAuthTokenTypes) -> None:
        # When giving an expired refresh token (with all other parameters correct),
        # a 400 response with the most cryptic error comes back from the Jive side:
        REFRESH_TOKEN_NO_LONGER_REFRESHABLE_JIVE_RESPONSE_DATA = {"error": "invalid_request", "error_description": "Required parameter(s) missing or wrong."}

        try:
            response.raise_for_status()
        except Exception as e:
            msg = f"Jive: Problem occurred from auth response"
            if response is not None:
                response_data = safe_get_response_json(response)
                if token_type == OAuthTokenTypes.REFRESH_TOKEN and response_data == REFRESH_TOKEN_NO_LONGER_REFRESHABLE_JIVE_RESPONSE_DATA:
                    raise RefreshTokenNoLongerRefreshableException(f"{msg} response_data='{response_data}'")
                if response.text:
                    msg = f"{msg}. Response text: '{response.text}'"
            raise Exception(msg)

    def __parse_token_response(self, response: requests.Response, token_type: OAuthTokenTypes) -> None:
        """
        Called by first time exchange_code and refresh_for_new_token

        Assume a json response with a minimum of an `access_token` and `refresh_token` key.
        """

        body = response.json()

        log.info(f"Jive: Successfully {self._logging_prefix.get(token_type)} for self._jive_api_credentials.id={self._jive_api_credentials.id if self._jive_api_credentials else ''}")
        try:
            self._access_token: str = body["access_token"]
            self._account_key: Optional[str] = body.get("account_key")
            self._organizer_key: Optional[str] = body.get("organizer_key")
            self._scope: Optional[str] = body.get("scope")
            self._principal: Optional[str] = body.get("principal")  # email address associated to the account
            self._refresh_token: str = body["refresh_token"]
            self._access_token_expires_at: datetime = timezone.now() + timedelta(seconds=body["expires_in"])
        except (KeyError, IndexError) as exc:
            log.debug(f"Jive: invalid token response: {response.content}")
            raise APIResponseException("failed to parse token response") from exc

        if self._jive_api_credentials:
            self._jive_api_credentials.access_token = self._access_token
            self._jive_api_credentials.refresh_token = self._refresh_token
            self._jive_api_credentials.account_key = self._account_key
            self._jive_api_credentials.organizer_key = self._organizer_key
            if self._scope is not None:
                self._jive_api_credentials.scope
            self._jive_api_credentials.access_token_expires_at = self._access_token_expires_at
            if self._principal:
                self._jive_api_credentials.email = self._principal
            log.info(f"Saving self._jive_api_credentials to RDBMS: {self._jive_api_credentials.id}")
            self._jive_api_credentials.save()
            log.info(f"Saved self._jive_api_credentials to RDBMS: {self._jive_api_credentials.id}")


class JiveClient:
    """
    TODO: Save the refresh token to the cache and try using cache instead of DB
    """

    base_url: str = "https://api.jive.com"

    __auth: _Authentication
    __session: requests.Session

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        jive_api_credentials: Optional[JiveAPICredentials] = None,
        api_base_url: str = "",
    ):
        self.__auth = _Authentication(client_id=client_id, client_secret=client_secret, jive_api_credentials=jive_api_credentials)

        self.__session = requests.Session()
        self.__session.auth = self.__auth
        self.__jive_api_credentials = jive_api_credentials

        if api_base_url:
            self._base_url = api_base_url

    @property
    def jive_api_credentials(self):
        return self.__jive_api_credentials

    @property
    def refresh_token(self):
        return self.__auth.refresh_token

    @property
    def access_token(self):
        return self.__auth.access_token

    @property
    def principal(self):
        return self.__auth._principal

    @property
    def organizer_key(self):
        return self.__auth._organizer_key

    @property
    def scope(self):
        return self.__auth._scope

    @property
    def account_key(self):
        return self.__auth._account_key

    def refresh_for_new_token(self):
        self.__auth.refresh_for_new_token()

    def exchange_code(self, code: str, request_uri: str):
        """
        `GOTO API Reference <https://developer.goto.com/guides/HowTos/03_HOW_accessToken/>`
        """
        self.__auth.exchange_code(code, request_uri)

    def create_webhook_channel(self, jive_api_credentials: JiveAPICredentials, webhook_url: str, lifetime: int = 2592000) -> JiveChannel:
        """
        Create a record for the intended channel and request the channel from the Jive API.  If the request fails
        the record will be deleted.

        Note: lifetime set to 2592000 (30 days) is the maximum amount of time allowed by the GoTo server we are interfacing with.

        https://developer.goto.com/GoToConnect#tag/Channels

        dependency: channel type goes under channel data
        """
        signature = hashlib.sha256()
        signature.update(uuid.uuid4().bytes)
        signature = signature.hexdigest()

        channel = JiveChannel.objects.create(
            jive_api_credentials=jive_api_credentials, signature=signature, expires_at=timezone.now() + timedelta(seconds=lifetime)
        )
        endpoint = f"https://api.jive.com/notification-channel/v1/channels/{channel.name}"

        try:
            resp = self.__request(
                method="post",
                path=endpoint,
                json={
                    "channelLifetime": lifetime,
                    "webhookChannelData": {"webhook": {"url": webhook_url}, "channelType": "Webhook", "signature": {"sharedSecret": signature}},
                },
            )
            response_body = resp.json()
            resp.raise_for_status()

            log.info(f"Jive: POST to endpoint='{endpoint}' gave a response_body='{response_body}'")
            channel_id = response_body.get("channelId")
            channel.source_jive_id = channel_id
            channel.save()
            log.info(f"Jive: Updated channel='{channel}' channelId='{channel_id}'")

        except Exception as exc:
            message = f"Could not create channel in Jive, deleting from Peerlogic API."
            log.warning(message)
            channel.delete()
            message = f"Could not create channel in Jive, deleted from Peerlogic API."
            raise APIResponseException(message) from exc

        return channel

    def refresh_channel_lifetime(self, channel: JiveChannel):
        """
        Extend the channel lifetime by the default value configured by the Jive API
        """
        endpoint = f"https://api.jive.com/notification-channel/v1/channels/{channel.name}/{channel.source_jive_id}/channel-lifetime"
        resp = self.__request(method="put", url=endpoint)

        resp.raise_for_status()
        response_body = resp.json()

        log.info(f"Jive: POST to endpoint='{endpoint}' gave a response_body='{response_body}'")

        channel.expires_at = timezone.now() + timedelta(seconds=response_body.get("channelLifetime"))
        channel.save()

    def delete_webhook_channel(self, channel: JiveChannel) -> JiveChannel:
        endpoint = f"https://api.jive.com/notification-channel/v1/channels/{channel.name}/{channel.source_jive_id}"

        log.info(f"Jive: Sending DELETE to endpoint='{endpoint}'")
        resp = self.__request(method="delete", url=endpoint)
        log.info(f"Jive: Sent DELETE to endpoint='{endpoint}'. Verifying status.")
        resp.raise_for_status()
        log.info(f"Jive: DELETE to endpoint='{endpoint}' successful - no response body.")

        log.info(f"Jive: Saving JiveChannel channel='{channel}' with active=False")
        channel.active = False
        channel.save()
        log.info(f"Jive: Saved JiveChannel channel='{channel}' with active=False")

        return channel

    def create_session(self, channel: JiveChannel) -> JiveSession:
        """
        Create a session on the Jive API and record the reference url.

        https://developer.goto.com/GoToConnect#tag/Sessions/paths/~1v2~1session/post

        dependency: channelID not channel Id
        """
        resp = self.__request(method="post", url="https://realtime.jive.com/v2/session", json={"channelId": channel.source_jive_id})
        resp.raise_for_status()
        body = resp.json()

        try:
            log.info(f"Jive Session Created - response body='{body}'")
            log.info(f"Saving Jive Session to the database: channel='{channel}', url={body['self']}")
            session = JiveSession.objects.create(channel=channel, url=body["self"])
            log.info(f"Saved session.id='{session.id}' to the database")
            return session
        except KeyError as exc:
            raise APIResponseException("failed to parse session response") from exc

    def create_session_dialog_subscription(self, session: JiveSession, *lines: Line):
        """
        Subscribe to the given lines on the given subscription.  A record is created for each line added to the session.

        https://developer.goto.com/GoToConnect#tag/Sessions/paths/~1v2~1session~1{sessionId}~1subscriptions/post
        """
        self.__request(
            method="post",
            url=session.url + "/subscriptions",
            json=[
                {"id": line.line_id, "type": "dialog", "entity": {"id": line.line_id, "type": "line.v2", "account": line.source_organization_jive_id}}
                for line in lines
            ],
        ).raise_for_status()

        JiveLine.objects.bulk_create(
            [JiveLine(session=session, source_jive_id=line.line_id, source_organization_jive_id=line.source_organization_jive_id) for line in lines],
            ignore_conflicts=True,
        )

    def list_lines(self) -> List[Line]:
        """
        List only lines available to the user only; not their organization's lines.

        https://developer.goto.com/GoToConnect/#tag/Lines/paths/~1users~1v1~1lines/get
        """
        lines: List[Line] = []

        resp = self.__request(method="get", path="/users/v1/lines")
        resp.raise_for_status()
        body = resp.json()

        try:
            for item in body["items"]:
                lines.append(Line(line_id=item["id"], source_organization_jive_id=item["organization"]["id"]))
        except KeyError as exc:
            raise APIResponseException("Jive: failed to parse list lines response") from exc

        return lines

    def list_lines_all_users(self, account_key: str) -> List[Line]:
        """
        List all lines available to all the user's account and pair them with their given organization id.

        https://developer.goto.com/GoToConnect/#tag/Users/paths/~1users~1v1~1users/get
        """

        lines: List[Line] = []

        resp = self.__request(method="get", path=f"/users/v1/users?accountKey={account_key}")
        resp.raise_for_status()
        body = resp.json()

        try:
            for item in body.get("items", []):
                item_lines = item.get("lines", [])
                for item_line in item_lines:
                    lines.append(Line(line_id=item_line["id"], source_organization_jive_id=item_line["organization"]["id"]))
        except KeyError as exc:
            raise APIResponseException("Jive: Failed to parse list_lines_all_users response") from exc

        return lines

    def __request(self, path: str = "", *args, **kwargs) -> requests.Response:
        if not kwargs.get("url"):
            kwargs["url"] = urllib.parse.urljoin(self.base_url, path)

        if not kwargs.get("headers"):
            kwargs["headers"] = {}

        if not kwargs["headers"].get("Content-Type"):
            kwargs["headers"]["Content-Type"] = "application/json"

        if not kwargs["headers"].get("Accept"):
            kwargs["headers"]["Accept"] = "application/json"

        response = self.__session.request(*args, **kwargs)

        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            log.info("Jive: Status code is a 401, refreshing for a new access and refresh token.")
            self.refresh_for_new_token()
            log.info("Jive: Done refreshing token.")
            # Retry:
            # TODO: PTECH-1568 remove these sensitive logs once we understand and solve why refreshes don't seem to be happening in time.
            log.info(f"Jive: Retrying original request with args='{args}' and kwargs='{kwargs}'")
            response = self.__session.request(*args, **kwargs)
            log.info(f"Jive: Retry response is '{response}' with original request args='{args}' and kwargs='{kwargs}'")
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                log.info(
                    f"Jive: Retry response still unauthorized, giving up. response.status_code='{response.status_code}' with original request args='{args}' and kwargs='{kwargs}'"
                )
                raise RefreshTokenNoLongerRefreshableException()

        return response
