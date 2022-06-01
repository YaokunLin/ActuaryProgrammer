import logging
import requests

from django.apps import apps as django_apps
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    ParseError,
    PermissionDenied,
)

import xmltodict

from core.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
)


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
        jwt_token = self.validate_header_and_get_token_value(request)

        # delegate authentication
        try:
            response = self.introspect_token(jwt_token)
        except AuthenticationFailed:
            log.info(f"Netsapiens Authentication failed with token {jwt_token}, trying the next Authentication class.")
            return None

        payload = xmltodict.parse(response)["Oauthtoken"]

        # authentication succeeded from auth system, obtain user from ours
        USER_MODEL = self.get_user_model()
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

    def get_user_model(self):
        return django_apps.get_model(settings.AUTH_USER_MODEL, require_ready=False)
