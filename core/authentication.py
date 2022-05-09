import logging
from typing import Dict
import requests


from django.apps import apps as django_apps
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

import xmltodict


logger = logging.getLogger(__name__)


class JSONWebTokenAuthentication(BaseAuthentication):
    """Token based authentication using the JSON Web Token standard."""

    def authenticate(self, request):
        """Entrypoint for Django Rest Framework"""

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

        return (user, None)

    def validate_header_and_get_token_value(self, request_object) -> str:
        """Obtain the access token from the appropriate header."""

        auth_header_name = "Authorization"
        auth_header_value = request_object.headers.get(auth_header_name, None)
        if not auth_header_value:
            raise AuthenticationFailed(f"'{auth_header_name}' header is required")

        auth_parts = auth_header_value.split(" ")

        if len(auth_parts) != 2:
            raise AuthenticationFailed(f"'{auth_header_name}' header is invalid. Received: '{auth_header_value}'")

        token_type, token = auth_parts
        token_type_expected = "Bearer"
        if token_type.lower() != token_type_expected.lower():
            raise AuthenticationFailed(f"'{auth_header_name}' header must be a '{token_type_expected}' token")

        # make sure it's not empty
        if not token:
            raise AuthenticationFailed(f"'{auth_header_name}' is missed a Bearer token value")

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
