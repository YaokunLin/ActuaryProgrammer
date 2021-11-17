import logging
from typing import Dict
import requests


from django.apps import apps as django_apps
from django.conf import settings
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication, get_authorization_header

import xmltodict


logger = logging.getLogger(__name__)


class JSONWebTokenAuthentication(BaseAuthentication):
    """Token based authentication using the JSON Web Token standard."""

    def authenticate(self, request):
        """Entrypoint for Django Rest Framework"""

        jwt_token = self.get_jwt_token(request)

        if jwt_token is None:
            return None

        response = self.introspect_token(jwt_token)
        payload = xmltodict.parse(response)["Oauthtoken"]


        USER_MODEL = self.get_user_model()
        user = USER_MODEL.objects.get_or_create_from_token_payload(payload)
        print(user)
        return (user, None)

    def introspect_token(self, token: str):
        url = settings.NETSAPIENS_INTROSPECT_TOKEN_URL
        headers = {"Authorization": f"Bearer {token}"}
        data = {"access_token": token}

        with requests.Session() as session:
            response = session.get(url, headers=headers, data=data)
            if not response.ok:
                raise AuthenticationFailed()

            return response.content

    def get_user_model(self):
        return django_apps.get_model(settings.AUTH_USER_MODEL, require_ready=False)

    def get_jwt_token(self, request):
        auth = get_authorization_header(request).split()
        if not auth or smart_text(auth[0].lower()) != "bearer":
            return None

        if len(auth) == 1:
            msg = _("Invalid Authorization header. No credentials provided.")
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid Authorization header. Credentials string " "should not contain spaces.")
            raise AuthenticationFailed(msg)

        return auth[1].decode()

    def authenticate_header(self, request):
        """
        Method required by the DRF in order to return 401 responses for authentication failures, instead of 403.
        More details in https://www.django-rest-framework.org/api-guide/authentication/#custom-authentication.
        """
        return "Bearer: api"
