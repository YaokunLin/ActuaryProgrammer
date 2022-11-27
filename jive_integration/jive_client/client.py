import hashlib
import logging
import urllib.parse
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from django.utils import timezone
from rest_framework import status
from requests.auth import AuthBase, HTTPBasicAuth

from jive_integration.models import JiveChannel, JiveAPICredentials, JiveLine, JiveSession

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


class _Authentication(AuthBase):
    _authentication_url: str = "https://authentication.logmeininc.com"
    _goto_api_url: str = "https://api.getgo.com"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        jive_api_credentials: Optional[JiveAPICredentials] = None,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._account_key = None
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._jive_api_credentials = jive_api_credentials

    def __call__(self, r: requests.Request):
        """
        Before sending the request check if the access token is present. If not, update the outgoing
        request with a valid access token header.
        """
        if not self._access_token:
            self._refresh_for_new_token()

        r.headers["Authorization"] = "Bearer " + self._access_token

        return r

    @property
    def access_token(self):
        return self._access_token

    @property
    def refresh_token(self):
        return self._refresh_token

    def _refresh_for_new_token(self):
        """
        Exchange the refresh token for a valid access token.

        https://developer.goto.com/guides/HowTos/05_HOW_refreshToken/
        """
        resp: requests.Response = requests.request(
            method="post",
            url=urllib.parse.urljoin(self._goto_api_url, "/oauth/v2/token"),
            auth=HTTPBasicAuth(self._client_id, self._client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        )

        self.__parse_token_response(resp)

    def exchange_code(self, code: str, redirect_uri: str):
        """
        Exchange the given authorization code for a refresh and access token.

        https://developer.goto.com/Authentication/#section/Authorization-Flows/Authorization-Code-Grant

        Scroll to 2. Exchange the authorization code for an access token
        """

        resp: requests.Response = requests.request(
            method="post",
            url=urllib.parse.urljoin(self._authentication_url, "/oauth/token"),
            auth=HTTPBasicAuth(self._client_id, self._client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "client_id": self._client_id},
        )

        self.__parse_token_response(resp)

    def __parse_token_response(self, resp: requests.Response) -> None:
        """
        Assume a json response with a minimum of an `access_token` and `refresh_token` key.
        """
        try:
            resp.raise_for_status()
        except Exception as e:
            msg = f"Problem occurred parsing token response"
            if resp is not None and resp.text:
                msg = f"{msg}. Response text: '{resp.text}'"
            raise Exception(msg)

        body = resp.json()

        try:
            self._access_token: str = body["access_token"]
            self._account_key: Optional[str] = body.get("account_key")
            self._organizer_key: Optional[str] = body.get("organizer_key")
            self._scope: Optional[str] = body.get("scope")
            self._principal: Optional[str] = body.get("principal")  # email address associated to the account
            self._refresh_token: str = body["refresh_token"]
            # TODO: save off __token_expires_at
            self.__token_expires_at: float = (datetime.utcnow() + timedelta(seconds=body["expires_in"])).timestamp()
        except (KeyError, IndexError) as exc:
            logging.debug(f"invalid token response: {resp.content}")
            raise APIResponseException("failed to parse token response") from exc

        if self._jive_api_credentials:
            self._jive_api_credentials.access_token = self._access_token
            self._jive_api_credentials.refresh_token = self._refresh_token
            self._jive_api_credentials.account_key = self._account_key
            self._jive_api_credentials.organizer_key = self._organizer_key
            self._jive_api_credentials.scope = self._scope
            self._jive_api_credentials.email = self._principal
            # TODO: save off __token_expires_at
            self._jive_api_credentials.save()


class JiveClient:
    """

    TODO: 1. accept a JiveAPICredentials
    TODO: 2. save the refresh token to the cache and DATABASE in parents
    TODO: 3. change the above functionality in step 2 - refresh token to the cache and DATABASE in client directly
    """

    base_url: str = "https://api.jive.com"

    __auth: _Authentication
    __session: requests.Session

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
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
        self.__auth._refresh_for_new_token()

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

        channel = JiveChannel.objects.create(connection=jive_api_credentials, signature=signature, expires_at=timezone.now() + timedelta(seconds=lifetime))
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
            channel.source_jive_id = response_body.get("channelId")
            channel.save()
        except Exception as exc:
            log.warn(f"Could not create channel in Jive, deleting from Peerlogic API.")
            channel.delete()
            raise exc

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
            raise APIResponseException("failed to parse list lines response") from exc

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
            raise APIResponseException("Failed to parse list_lines_all_users response") from exc

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
            self.refresh_for_new_token()
            # Retry:
            response = self.__session.request(*args, **kwargs)

        return response
