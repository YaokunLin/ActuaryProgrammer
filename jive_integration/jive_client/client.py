import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import requests
import urllib.parse

from django.conf import settings
from django.utils import timezone
from requests.auth import HTTPBasicAuth, AuthBase

from jive_integration.models import JiveChannel, JiveSession, JiveConnection, JiveLine


class Line:
    """
    Given lines are constantly being used to compare sets of data this abstraction allows us to easily compare them.
    """

    def __init__(self, line_id: str, organization_id: str):
        self.line_id = line_id
        self.organization_id = organization_id

    def __hash__(self):
        return hash(self.line_id + self.organization_id)

    def __eq__(self, other):
        return self.line_id == other.line_id and self.organization_id == other.source_organization_jive_id


class APIResponseException(Exception):
    """
    Wraps any exception raised when parsing an API response.
    """

    pass


class _Authentication(AuthBase):
    _authentication_url: str = "https://authentication.logmeininc.com"
    _goto_api_url: str = "https://api.getgo.com"

    def __init__(self, client_id: str, client_secret: str, refresh_token: Optional[str] = None):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def __call__(self, r: requests.Request):
        """
        Before sending the request check if the access token has expired and refresh it if so.  Update the outgoing
        request with a valid access token header.
        """
        if not self._access_token or self.__token_expires_at < datetime.utcnow().timestamp():
            self._get_token()

        r.headers["Authorization"] = "Bearer " + self._access_token

        return r

    @property
    def refresh_token(self):
        return self._refresh_token

    def _get_token(self):
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

        https://developer.goto.com/guides/HowTos/03_HOW_accessToken/
        """

        resp: requests.Response = requests.request(
            method="post",
            url=urllib.parse.urljoin(self._authentication_url, "/oauth/token"),
            auth=HTTPBasicAuth(self._client_id, self._client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "client_id": self._client_id},
        )

        self.__parse_token_response(resp)

    def __parse_token_response(self, resp: requests.Response):
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
            self._access_token = body["access_token"]
            self._principal = body["principal"]  # email address associated to the account
            self._refresh_token = body["refresh_token"]
            self.__token_expires_at = (datetime.utcnow() + timedelta(seconds=body["expires_in"])).timestamp()
        except (KeyError, IndexError) as exc:
            logging.debug(f"invalid token response: {resp.content}")
            raise APIResponseException("failed to parse token response") from exc


class JiveClient:
    base_url: str = "https://api.jive.com"

    __auth: _Authentication
    __session: requests.Session

    def __init__(self, client_id: str, client_secret: str, refresh_token: Optional[str] = None, api_base_url: str = ""):
        self.__auth = _Authentication(client_id=client_id, client_secret=client_secret, refresh_token=refresh_token)

        self.__session = requests.Session()
        self.__session.auth = self.__auth

        if api_base_url:
            self._base_url = api_base_url

    @property
    def refresh_token(self):
        return self.__auth.refresh_token

    @property
    def access_token(self):
        return self.__auth._access_token

    @property
    def principal(self):
        return self.__auth._principal

    def exchange_code(self, code: str, request_uri: str):
        """
        `GOTO API Reference <https://developer.goto.com/guides/HowTos/03_HOW_accessToken/>`
        """
        self.__auth.exchange_code(code, request_uri)

    def create_webhook_channel(self, connection: JiveConnection, webhook_url: str, lifetime: int = 518400) -> JiveChannel:
        """
        Create a record for the intended channel and request the channel from the Jive API.  If the request fails
        the record will be deleted.

        https://developer.goto.com/GoToConnect#tag/Channels

        dependency: channel type goes under channel data
        """
        signature = hashlib.sha256()
        signature.update(uuid.uuid4().bytes)
        signature = signature.hexdigest()

        channel = JiveChannel.objects.create(connection=connection, signature=signature, expires_at=timezone.now() + timedelta(seconds=lifetime))

        try:
            resp = self.__request(
                method="post",
                path=f"https://api.jive.com/notification-channel/v1/channels/{channel.name}",
                json={
                    "channelLifetime": lifetime,
                    "webhookChannelData": {"webhook": {"url": webhook_url}, "channelType": "Webhook", "signature": {"sharedSecret": signature}},
                },
            )
            channel.source_jive_id = resp.json()["channelId"]
            channel.save()

            resp.raise_for_status()
        except Exception as exc:
            channel.delete()
            raise exc

        return channel

    def refresh_channel_lifetime(self, channel: JiveChannel):
        """
        Extend the channel lifetime by the default value configured by the Jive API
        """
        resp = self.__request(method="put", url=f"https://api.jive.com/notification-channel/v1/channels/{channel.name}/{channel.external_id}/channel-lifetime")

        resp.raise_for_status()

        channel.expires_at = timezone.now() + timedelta(seconds=resp.json()["channelLifetime"])
        channel.save()

    def create_session(self, channel: JiveChannel) -> JiveSession:
        """
        Create a session on the Jive API and record the reference url.

        https://developer.goto.com/GoToConnect#tag/Sessions/paths/~1v2~1session/post

        dependency: channelID not channel Id
        """
        resp = self.__request(method="post", url="https://realtime.jive.com/v2/session", json={"channelId": channel.external_id})

        resp.raise_for_status()

        body = resp.json()

        try:
            return JiveSession.objects.create(channel=channel, url=body["self"])
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
            json=[{"id": line.line_id, "type": "dialog", "entity": {"id": line.line_id, "type": "line.v2", "account": line.organization_id}} for line in lines],
        ).raise_for_status()

        JiveLine.objects.bulk_create(
            [JiveLine(session=session, external_id=line.line_id, organization_id=line.organization_id) for line in lines], ignore_conflicts=True
        )

    def list_lines(self) -> List[Line]:
        """
        List all lines avaialable to the user's account and pair them with their given organization id.

        https://developer.goto.com/GoToConnect#tag/Lines/paths/~1users~1v1~1lines/get
        """
        lines: List[Line] = []

        resp = self.__request(method="get", path="/users/v1/lines")

        resp.raise_for_status()

        body = resp.json()

        try:
            for item in body["items"]:
                lines.append(Line(line_id=item["id"], organization_id=item["organization"]["id"]))
        except KeyError as exc:
            raise APIResponseException("failed to parse list lines response") from exc

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

        return self.__session.request(*args, **kwargs)
