import logging

import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import ugettext as _
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope
from pydantic import BaseModel

from rest_framework import status, views, viewsets
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    ParseError,
    PermissionDenied,
)
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView


from core.exceptions import InternalServerError, ServiceUnavailableError
from core.field_choices import IndustryTypes, VoipProviderIntegrationTypes
from core.models import (
    Agent,
    Client,
    Patient,
    Practice,
    PracticeTelecom,
    User,
    VoipProvider,
)
from core.serializers import (
    AdminUserSerializer,
    AgentSerializer,
    MyProfileAgentSerializer,
    ClientSerializer,
    MyProfileUserSerializer,
    PatientSerializer,
    PracticeSerializer,
    AdminPracticeTelecomSerializer,
    AdminVoipProviderSerializer,
    PracticeTelecomSerializer,
    VoipProviderSerializer,
)
from core.setup_user_and_practice import (
    create_agent,
    create_user_telecom,
    save_user_activity_and_token,
    setup_practice,
    setup_user,
    update_user_on_refresh,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class ServiceUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Service unavailable. Try again later.")
    default_code = "service_unavailable_error"


class CoreFieldChoicesView(views.APIView):
    def get(self, request, format=None):
        result = {}
        result["industry_types"] = dict((y, x) for x, y in IndustryTypes.choices)
        # excluding VoipProviderIntegrationTypes.choices - our integration types are secret. (Use /voip-providers/)
        return Response(result)


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
        netsapiens_client: requests.Session = settings.NETSAPIENS_SYSTEM_CLIENT,
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

    def get_queryset(self):
        patient_qs = Patient.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            patient_qs = Patient.objects.all()
        elif self.request.method in SAFE_METHODS:
            # TODO: organizations ACL
            # Can see any patients if you are an assigned agent to a practice
            practice_ids = Agent.objects.filter(user=self.request.user).values_list("practice_id", flat=True)
            patient_qs = Patient.objects.filter(practice__id__in=practice_ids)

        return patient_qs.order_by("-modified_at")


class PracticeViewSet(viewsets.ModelViewSet):
    serializer_class = PracticeSerializer
    filterset_fields = ["active"]
    search_fields = ["name"]

    def get_queryset(self):

        query_set = Practice.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            query_set = Practice.objects.all()
        elif self.request.method in SAFE_METHODS:
            # TODO: organizations ACL
            # Can see any practice if you are an assigned agent to a practice
            practice_ids = Agent.objects.filter(user=self.request.user).values_list("practice_id", flat=True)
            query_set = Practice.objects.filter(pk__in=practice_ids)

        return query_set.order_by("name")

    def create(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().create(request=request)

    def update(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().update(request=request)

    def partial_update(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().partial_update(request=request)


class PracticeTelecomViewSet(viewsets.ModelViewSet):
    queryset = PracticeTelecom.objects.all().order_by("-modified_at")
    filterset_fields = ["domain", "phone_sms", "phone_callback", "voip_provider"]
    serializer_class_write = AdminPracticeTelecomSerializer
    serializer_class_read = PracticeTelecomSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        practice_telecoms_qs = PracticeTelecom.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            practice_telecoms_qs = PracticeTelecom.objects.all()
        elif self.request.method in SAFE_METHODS:
            # TODO: organizations ACL
            # Can see any practice telecoms if you are an assigned agent to a practice
            practice_ids = Agent.objects.filter(user=self.request.user).values_list("practice_id", flat=True)
            practice_telecoms_qs = PracticeTelecom.objects.filter(practice__id__in=practice_ids)

        return practice_telecoms_qs.order_by("-modified_at")

    def create(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().create(request=request)

    def update(self, request, pk=None):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().update(request=request, pk=pk)

    def partial_update(self, request, pk=None):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().partial_update(request=request, pk=pk)


class VoipProviderViewset(viewsets.ModelViewSet):
    """VOIP Providers are unique - we want users to be able to select them as an integration partner with us"""

    queryset = VoipProvider.objects.all().order_by("-modified_at")

    filterset_fields = ["company_name"]
    serializer_class_write = AdminVoipProviderSerializer
    serializer_class_read = VoipProviderSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def create(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().create(request=request)

    def update(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().update(request=request)

    def partial_update(self, request):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        super().partial_update(request=request)


class AgentViewset(viewsets.ModelViewSet):
    queryset = Agent.objects.all().order_by("-practice").select_related("user")
    serializer_class = AgentSerializer
    filterset_fields = ["practice"]

    def get_queryset(self):
        agents_qs = Agent.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            agents_qs = Agent.objects.all()
        elif self.request.method in SAFE_METHODS:
            # TODO: organizations ACL
            # Can see any agents if you are an assigned agent to a practice
            practice_ids = Agent.objects.filter(user=self.request.user).values_list("practice_id", flat=True)
            agents_qs = Agent.objects.filter(practice__id__in=practice_ids)

        return agents_qs.order_by("-modified_at")


class MyProfileView(RetrieveUpdateAPIView):
    def get(self, request, format=None):
        user = User.objects.get(pk=self.request.user.id)
        serializer = MyProfileUserSerializer(user)
        return Response(data=serializer.data)

    def patch(self, request, format=None):
        user = User.objects.get(pk=self.request.user.id)
        serializer = MyProfileUserSerializer(user, data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)
        serializer.save()
        return Response(data=serializer.data)


class AdminUserViewset(viewsets.ModelViewSet):
    """
    Used by Auth0 for user creation. Not for any other use.
    """

    queryset = User.objects.all().order_by("-modified_at")
    permission_classes = [TokenHasReadWriteScope]
    serializer_class = AdminUserSerializer
