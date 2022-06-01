import logging

from django.conf import settings
from django.db import transaction
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
)
from django.utils import timezone
from django.utils.translation import ugettext as _
from pydantic import BaseModel
from rest_framework import viewsets
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    ParseError,
    PermissionDenied,
)
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
)
from core.setup_user_and_practice import create_agent, create_user_telecom, save_user_activity_and_token, setup_practice, setup_user, update_user_on_refresh
from .models import Client, Patient, Practice, PracticeTelecom, VoipProvider
from .serializers import ClientSerializer, PatientSerializer, PracticeSerializer, PracticeTelecomSerializer, VoipProviderSerializer


# Get an instance of a logger
log = logging.getLogger(__name__)


class ServiceUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Service unavailable. Try again later.")
    default_code = "service_unavailable_error"


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    class NetsapiensAuthToken(BaseModel):
        # Expected format as of 2022-02-22
        access_token: str  # alphanumberic
        apiversion: str  # e.g. "Version: 41.2.3"
        client_id: str  # peerlogic-api-{ENVIRONMENT}
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
        client_id: str  # peerlogic-api-{ENVIRONMENT}
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
        default_handler = self._login_to_netsapiens
        grant_handler_map = {
            "password": default_handler,
            "refresh_token": self._refresh_token_with_netsapiens,
        }

        netsapiens_access_token_response = None

        try:
            grant_type = request.data.get("grant_type")
            handler = grant_handler_map.get(grant_type, default_handler)
            netsapiens_access_token_response = handler(request)

            return netsapiens_access_token_response
        except APIException as api_exception:
            # pass it through
            raise api_exception
        except Exception as e:
            # unexpected exceptions 500 internal server error
            log.exception(e)
            return Response(status=500, data={"detail": "Server Error"})

    #
    # login / password grant
    #

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
            raise ParseError()

        data = {
            "grant_type": "password",
            "format": "json",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        }

        netsapiens_access_token_response = netsapiens_client.request("POST", settings.NETSAPIENS_ACCESS_TOKEN_URL, data=data)
        self._validate_netsapiens_status_code(netsapiens_access_token_response)

        response_json = netsapiens_access_token_response.json()
        netsapiens_auth_token = LoginView.NetsapiensAuthToken.parse_obj(response_json)
        self._setup_user_and_save_activity(netsapiens_auth_token)

        return Response(status=200, data=netsapiens_access_token_response.json())

    def _setup_user_and_save_activity(self, netsapiens_auth_token: NetsapiensAuthToken) -> None:
        now = timezone.now()

        with transaction.atomic():
            user, user_created = setup_user(
                username=netsapiens_auth_token.username,
                name=netsapiens_auth_token.displayName,
                email=netsapiens_auth_token.user_email,
                domain=netsapiens_auth_token.domain,
                login_time=now,
            )
            save_user_activity_and_token(
                access_token=netsapiens_auth_token.access_token,
                refresh_token=netsapiens_auth_token.refresh_token,
                login_time=now,
                expires_in_seconds=netsapiens_auth_token.expires_in,
                user=user,
            )

            if user_created:
                create_user_telecom(user)
                practice, _ = setup_practice(netsapiens_auth_token.domain)
                create_agent(user, practice)

    #
    # Refresh flow
    #

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
        self._validate_netsapiens_status_code(netsapiens_access_token_response)

        netsapiens_response_json = netsapiens_access_token_response.json()
        netsapiens_refresh_token = LoginView.NetsapiensRefreshToken.parse_obj(netsapiens_response_json)
        self._update_user_and_save_activity(netsapiens_refresh_token=netsapiens_refresh_token)

        return Response(status=200, data=netsapiens_access_token_response.json())

    def _update_user_and_save_activity(self, netsapiens_refresh_token: NetsapiensRefreshToken) -> None:
        now = timezone.now()

        with transaction.atomic():
            update_user_on_refresh(
                username=netsapiens_refresh_token.uid,
                login_time=now,
            )

    def _validate_netsapiens_status_code(self, netsapiens_access_token_response):
        # bad client id or secret: 400
        # missing required field: 400
        if netsapiens_access_token_response.status_code == 400:
            log.exception(
                f"Encountered 400 error when attempting to authenticate with Netsapiens! We may have an invalid client_id, client_secret, missing field, or coding problem in the Peerlogic API."
            )
            raise InternalServerError(f"Unable to authenticate. Authentication service is misconfigured. Please contact support.")

        # bad username or password: 403
        if netsapiens_access_token_response.status_code == 403:
            log.exception(
                f"NetsapiensJSONWebTokenAuthentication#introspect_token: Netsapiens denied user permissions / found user had insufficient scope! This may or may not be a problem since we aren't using scopes to determine access from them."
            )
            raise PermissionDenied()

        # netsapiens server problem: 500s
        if netsapiens_access_token_response.status_code >= 500:
            log.exception(
                f"NetsapiensJSONWebTokenAuthentication#introspect_token: Encountered 500 error when attempting to authenticate with Netsapiens! Netsapiens may be down or an invalid url is being used!"
            )
            raise ServiceUnavailableError(f"Authentication service unavailable for Peerlogic API. Please contact support.")

        if not netsapiens_access_token_response.ok:
            log.warning("NetsapiensJSONWebTokenAuthentication#introspect_token: response not ok!")
            raise AuthenticationFailed()

        return None


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
