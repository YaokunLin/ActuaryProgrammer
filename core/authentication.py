import logging
from typing import Dict
import requests


from django.apps import apps as django_apps
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    ParseError,
)
from rest_framework.authentication import BaseAuthentication

import xmltodict


logger = logging.getLogger(__name__)


class JSONWebTokenAuthentication(BaseAuthentication):
    """Token based authentication using the JSON Web Token standard."""
    token_type_expected = "Bearer"

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        https://www.django-rest-framework.org/api-guide/authentication/#custom-authentication
        https://www.django-rest-framework.org/api-guide/permissions/#how-permissions-are-determined
        """
        return f"{JSONWebTokenAuthentication.token_type_expected}"

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
        response = self.introspect_token(jwt_token)
        payload = xmltodict.parse(response)["Oauthtoken"]

        # obtain user
        USER_MODEL = self.get_user_model()
        user = USER_MODEL.objects.get_and_update_from_introspect_token_payload(payload)

        if user is None:
            logger.exception("JSONWebTokenAuthentication#authenticate: user not found or created!")
            raise AuthenticationFailed(f"Malformed auth request")

        return (user, None)

    def validate_header_and_get_token_value(self, request_object) -> str:
        """Obtain the access token from the appropriate header."""

        auth_header_name = "Authorization"
        auth_header_value = request_object.headers.get(auth_header_name, None)
        if not auth_header_value:
            # w3c says it SHOULD NOT have a payload in this case, so it's optional but valuable to give clients some information. It would require additional
            # work to make django not include a value in the response
            raise NotAuthenticated(f"'{auth_header_name}' header is required")

        message_for_expected_auth_value = "Received value: '{auth_header_value}' Expected value: '{token_type_expected} <token>'"
        auth_parts = auth_header_value.split(" ")
        token_type_expected = JSONWebTokenAuthentication.token_type_expected
        if len(auth_parts) != 2:
            raise ParseError(f"'{auth_header_name}' header value is invalid. {message_for_expected_auth_value}")

        token_type, token = auth_parts
        if token_type.lower() != JSONWebTokenAuthentication.token_type_expected.lower():
            raise ParseError(f"'{auth_header_name}' header value must be a '{token_type_expected}' token. {message_for_expected_auth_value}")

        # make sure it's not empty, theoretically impossible and should be caught by length checks above
        if not token:
            raise ParseError(f"'{auth_header_name}' is missing a Bearer token value. {message_for_expected_auth_value}")

        return token

    def introspect_token(self, token: str):
        url = settings.NETSAPIENS_INTROSPECT_TOKEN_URL
        headers = {"Authorization": f"Bearer {token}"}
        data = {"access_token": token}

        with requests.Session() as session:
            response = session.get(url, headers=headers, data=data)
            if not response.ok:
                logger.exception("JSONWebTokenAuthentication#introspect_token: response not ok!")
                raise AuthenticationFailed()

            return response.content

    def get_user_model(self):
        return django_apps.get_model(settings.AUTH_USER_MODEL, require_ready=False)
