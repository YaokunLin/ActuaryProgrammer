import json
import logging

import requests
import xmltodict
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache, caches
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.oauth2_backends import get_oauthlib_core
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    ParseError,
    PermissionDenied,
)

from core.exceptions import InternalServerError, ServiceUnavailableError
from peerlogic.settings import (
    CACHE_NAME_AUTH_IN_MEMORY,
    CACHE_TIME_AUTH_MEMORY_SECONDS,
    CACHE_TIME_AUTH_REDIS_SECONDS,
)

User = get_user_model()

log = logging.getLogger(__name__)


class NetsapiensJSONWebTokenAuthentication(BaseAuthentication):
    """Token based authentication using the JSON Web Token standard."""

    token_type_expected = "Bearer"

    def authenticate_header(self, request) -> str:
        """
        Return a string to be used as the value of the `WWW-Authenticate` header in a `401 Unauthenticated` response, or `None` if the authentication scheme
        should return `403 Permission Denied` responses.
        https://www.django-rest-framework.org/api-guide/authentication/#custom-authentication
        https://www.django-rest-framework.org/api-guide/permissions/#how-permissions-are-determined
        """
        return f"{NetsapiensJSONWebTokenAuthentication.token_type_expected}"  # usually includes a realm="" but our implementation does not have an appropriate value

    def authenticate(self, request):
        """Entrypoint for Django Rest Framework
        Standards for status codes from: https://tools.ietf.org/id/draft-ietf-oauth-v2-bearer-22.xml#resource-error-codes

        When a request fails, the resource server responds using the appropriate HTTP status code (typically, 400, 401, 403, or 405), and includes one of the
        following error codes in the response:

        * invalid_request - The request is missing a required parameter, includes an unsupported parameter or parameter value, repeats the same parameter, uses
                            more than one method for including an access token, or is otherwise malformed. The resource server SHOULD respond with the HTTP 400
                            (Bad Request) status code.
        * invalid_token - The access token provided is expired, revoked, malformed, or invalid for other reasons. The resource SHOULD respond with the HTTP 401
                            (Unauthorized) status code. The client MAY request a new access token and retry the protected resource request.
        * insufficient_scope - The request requires higher privileges than provided by the access token. The resource server SHOULD respond with the HTTP 403
                            (Forbidden) status code and MAY include the scope attribute with the scope necessary to access the protected resource.

        If the request lacks any authentication information (e.g., the client was unaware authentication is necessary or attempted using an unsupported
        authentication method), the resource server SHOULD NOT include an error code or other error information.
        """

        # extract token
        token = self.validate_header_and_get_token_value(request)

        if not token or len(token) > 64:
            # HEREBEDRAGONS: NETSAPIENS tokens are seemingly all 32-length bearer tokens at present, not long JWTs
            # core1-phx.peerlogic.com - NsApi.oauth_codes.code (varchar(64)).
            # count of code lengths on 2022-09-19
            ## select LENGTH(code), count(*) from NsApi.oauth_codes group by LENGTH(code)
            ## length 6 - count 7
            ## length 32 - count 1020
            return None

        redis_cache = cache
        memory_cache = caches[CACHE_NAME_AUTH_IN_MEMORY]
        cache_key = f"{self.__class__.__name__}{token}"
        cached_result = memory_cache.get(cache_key, None)
        bad_token_cache_value = {"bad_token": True}
        if cached_result is None:
            cached_result = redis_cache.get(cache_key, None)
            if cached_result is None:
                try:
                    response = self.introspect_token(token)
                except AuthenticationFailed:
                    log.info("Netsapiens Authentication failed. Trying the next Authentication class.")
                    payload = bad_token_cache_value
                else:
                    payload = xmltodict.parse(response)["Oauthtoken"]

                redis_cache.set(cache_key, json.dumps(payload), CACHE_TIME_AUTH_REDIS_SECONDS)
                memory_cache.set(cache_key, json.dumps(payload), CACHE_TIME_AUTH_MEMORY_SECONDS)
            else:
                payload = json.loads(cached_result)
                memory_cache.set(cache_key, json.dumps(payload), CACHE_TIME_AUTH_REDIS_SECONDS)
        else:
            payload = json.loads(cached_result)

        if payload == bad_token_cache_value:
            return None

        # authentication succeeded from auth system, obtain user from ours
        USER_MODEL = get_user_model()
        user = USER_MODEL.objects.get_and_update_from_introspect_token_payload(payload)

        if user is None:
            log.exception("NetsapiensJSONWebTokenAuthentication#authenticate: user not found or created!")
            raise InternalServerError("Encountered an error while trying to obtain authenticated user from Peerlogic API system!")

        return (user, None)

    def validate_header_and_get_token_value(self, request_object) -> str:
        """Obtain the access token from the appropriate header."""

        auth_header_name = "Authorization"
        auth_header_value = request_object.headers.get(auth_header_name, None)
        if not auth_header_value:
            # w3c says it SHOULD NOT have a payload in this case, so it's optional but valuable to give clients some information. It would require additional
            # work to make django not include a value in the response
            raise NotAuthenticated(f"'{auth_header_name}' header is required")

        token_type_expected = NetsapiensJSONWebTokenAuthentication.token_type_expected
        message_for_expected_auth_value = f"Received value: '{auth_header_value}' Expected value: '{token_type_expected} <token>'"
        auth_parts = auth_header_value.split(" ")
        if len(auth_parts) != 2:
            raise ParseError(f"'{auth_header_name}' header value is invalid. {message_for_expected_auth_value}")

        token_type, token = auth_parts
        if token_type.lower() != NetsapiensJSONWebTokenAuthentication.token_type_expected.lower():
            raise ParseError(f"'{auth_header_name}' header value must be a '{token_type_expected}' token. {message_for_expected_auth_value}")

        # make sure it's not empty, theoretically impossible and should be caught by length checks above
        if not token:
            raise ParseError(f"'{auth_header_name}' is missing a Bearer token value. {message_for_expected_auth_value}")

        return token

    def introspect_token(self, token: str) -> str:
        url = settings.NETSAPIENS_INTROSPECT_TOKEN_URL
        headers = {"Authorization": f"Bearer {token}"}
        data = {"access_token": token}

        with requests.Session() as session:
            response = session.get(url, headers=headers, data=data)

            # misconfiguration or coding problem in peerlogic api
            # examples:
            # missing Authorization header: 400
            # missing "Bearer": 400
            # mispelled "Bearer" or other token type: 400
            if response.status_code == 400:
                log.exception(
                    f"NetsapiensJSONWebTokenAuthentication#introspect_token: Encountered 400 error when attempting to authenticate with Netsapiens! We may have an invalid Authentication header value, some other misconfiguration, or coding problem in the Peerlogic API."
                )
                raise InternalServerError(f"Unable to authenticate. Authentication service is misconfigured. Please contact support.")

            # Netsapiens permissions problem
            if response.status_code == 403:
                log.warning(
                    f"NetsapiensJSONWebTokenAuthentication#introspect_token: Netsapiens denied user permissions / found user had insufficient scope! This may or may not be a problem since we aren't using scopes to determine access from them."
                )
                return PermissionDenied()

            # problems with Netsapiens access / infrastructure!
            if response.status_code >= 500:
                log.exception(
                    f"NetsapiensJSONWebTokenAuthentication#introspect_token: Encountered 500 error when attempting to authenticate with Netsapiens! Netsapiens may be down or an invalid url is being used! Used url='{url}'."
                )
                raise ServiceUnavailableError(f"Authentication service unavailable for Peerlogic API. Please contact support.")

            # Everything else coerces into an authentication problem
            # missing token value: 401
            if not response.ok:
                log.warning("NetsapiensJSONWebTokenAuthentication#introspect_token: response not ok!")
                raise AuthenticationFailed()

            return response.content


class ClientCredentialsUserAuthentication(OAuth2Authentication):
    application_user_map = {settings.AUTH0_MACHINE_CLIENT_ID: settings.AUTH0_MACHINE_USER_ID}

    def _get_application_user(self, original_request, request_result):
        try:
            client_id = request_result.client.client_id
            user_id = ClientCredentialsUserAuthentication.application_user_map[client_id]
            request_result.user = User.objects.get(pk=user_id)
        except KeyError:
            log.warning(f"No application with given client_id exists in application_user_map={ClientCredentialsUserAuthentication.application_user_map}.")
            original_request.oauth2_error = getattr(request_result, "oauth2_error", {})
            return None
        except User.DoesNotExist:
            log.warning(f"User does not match with user id from application_user_map={ClientCredentialsUserAuthentication.application_user_map}")
            original_request.oauth2_error = getattr(request_result, "oauth2_error", {})
            return None

        return request_result

    def authenticate(self, original_request):
        """
        Returns two-tuple of (user, token) if authentication succeeds,
        or None otherwise.
        """
        oauthlib_core = get_oauthlib_core()
        valid, request_result = oauthlib_core.verify_request(original_request, scopes=[])
        if not valid:
            original_request.oauth2_error = getattr(request_result, "oauth2_error", {})
            return None
        if not request_result.user:
            request_result = self._get_application_user(original_request, request_result)

        return request_result.user, request_result.access_token
