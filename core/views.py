import logging
from typing import Dict

from django.conf import settings
from django.db import transaction
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
)
from django.utils import timezone
from pydantic import BaseModel
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.setup_user_and_practice import create_agent, create_user_telecom, save_user_activity_and_token, setup_practice, setup_user
from .models import Client, Patient, Practice, PracticeTelecom, VoipProvider
from .serializers import ClientSerializer, PatientSerializer, PracticeSerializer, PracticeTelecomSerializer, VoipProviderSerializer


# Get an instance of a logger
log = logging.getLogger(__name__)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

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

    def post(self, request, format=None):
        default_action = self._login_to_netsapiens
        grant_handler_map = {
            "password": default_action,
            "refresh_token": self._refresh_token_with_netsapiens,
        }

        netsapiens_access_token_response = None

        try:
            grant_type = request.data.get("grant_type")
            netsapiens_access_token_response = grant_handler_map.get(grant_type, default_action)(request)
            netsapiens_user = netsapiens_access_token_response.json()
            self._setup_user_and_save_activity(netsapiens_user)

            return Response(status=200, data=netsapiens_user)

        except Exception as e:
            log.exception(e)
            return Response(status=netsapiens_access_token_response.status_code, data={"error": e})

    def _login_to_netsapiens(
        self,
        request: HttpRequest,
        client_id: str = settings.NETSAPIENS_CLIENT_ID,
        client_secret: str = settings.NETSAPIENS_CLIENT_SECRET,
        netsapiens_client: str = settings.NETSAPIENS_SYSTEM_CLIENT,
    ) -> Response:

        username = request.data.get("username")
        password = request.data.get("password")

        log.info(f"User is attempting login. username='{username}'.")

        # validate
        if not (username and password):
            log.info(f"Bad Request detected for login. Missing one or more required fields.")
            return HttpResponseBadRequest("Missing one or more required fields: 'username' and 'password'")

        data = {
            "grant_type": "password",
            "format": "json",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        }

        netsapiens_access_token_response = netsapiens_client.request("POST", settings.NETSAPIENS_ACCESS_TOKEN_URL, data=data)
        netsapiens_access_token_response.raise_for_status()
        response_json = netsapiens_access_token_response.json()
        LoginView.NetsapiensAuthToken.parse_obj(response_json)

        return netsapiens_access_token_response

    def _refresh_token_with_netsapiens(
        self,
        request: HttpRequest,
        client_id: str = settings.NETSAPIENS_CLIENT_ID,
        client_secret: str = settings.NETSAPIENS_CLIENT_SECRET,
        netsapiens_client: str = settings.NETSAPIENS_SYSTEM_CLIENT,
    ) -> Response:

        refresh_token = request.data.get("refresh_token")

        log.info(f"User is attempting to refresh their access token.")

        data = {
            "grant_type": "refresh_token",
            "format": "json",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        # netsapiens uses a GET with query parameters
        # NOTE: this is done both ways in the field but the appropriate way may be for POSTs with body params
        netsapiens_access_token_response = netsapiens_client.request("GET", settings.NETSAPIENS_ACCESS_TOKEN_URL, params=data)
        netsapiens_access_token_response.raise_for_status()
        response_json = netsapiens_access_token_response.json()
        LoginView.NetsapiensRefreshToken.parse_obj(response_json)

        return netsapiens_access_token_response

    def _setup_user_and_save_activity(self, netsapiens_user: Dict) -> None:
        now = timezone.now()

        with transaction.atomic():
            user, user_created = setup_user(now, netsapiens_user)

            save_user_activity_and_token(now, netsapiens_user, user)

            if user_created:
                create_user_telecom(user)
                practice, _ = setup_practice(netsapiens_user["domain"])
                create_agent(user, practice)


class ClientViewset(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by("-modified_at")
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = Client.objects.all().order_by("-modified_at")
        practice_name = self.request.query_params.get("practice_name", None)
        if practice_name is not None:
            queryset = queryset.filter(practice__name=practice_name)
        return queryset


class PatientViewset(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by("-modified_at")
    serializer_class = PatientSerializer

    filterset_fields = ["phone_mobile", "phone_home", "phone_work", "phone_fax"]
    search_fields = ["name_first", "name_last", "phone_mobile", "phone_home", "phone_work"]


class PracticeViewSet(viewsets.ModelViewSet):
    queryset = Practice.objects.all().order_by("-modified_at")
    serializer_class = PracticeSerializer
    # TODO: provide filtering of queryset to logged in voip providers' practices

    search_fields = ["name"]


class PracticeTelecomViewSet(viewsets.ModelViewSet):
    queryset = PracticeTelecom.objects.all().order_by("-modified_at")
    serializer_class = PracticeTelecomSerializer
    # TODO: provide filtering of queryset to logged in voip providers' practices

    filterset_fields = ["domain", "phone_sms", "phone_callback", "voip_provider"]


class VoipProviderViewset(viewsets.ModelViewSet):
    queryset = VoipProvider.objects.all().order_by("-modified_at")
    serializer_class = VoipProviderSerializer

    filterset_fields = ["company_name"]
