import json
import logging

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from google.api_core.exceptions import PermissionDenied
from pydantic import BaseModel
from rest_framework import status, viewsets
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import APIException, ParseError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from ringcentral import SDK

from core.models import PracticeTelecom
from core.setup_user_and_practice import (
    create_agent,
    create_user_telecom,
    save_user_activity_and_token,
    setup_practice,
    setup_user,
)
from ringcentral_integration.models import (
    RingCentralAPICredentials,
    RingCentralCallLeg,
    RingCentralCallSubscription,
    RingCentralSessionEvent,
)
from ringcentral_integration.publishers import publish_call_create_call_record_event
from ringcentral_integration.serializers import (
    AdminRingCentralAPICredentialsSerializer,
    RingCentralCallLegSerializer,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class RingCentralAuthToken(BaseModel):
    access_token: str  # alphanumeric
    expires_in: int  # e.g. "3600"
    refresh_token: str  # alphanumeric
    refresh_token_expires_in: int  # "604800"
    refresh_token_expire_time: int  # "1664289200.5082414"
    scope: str  # e.g. "ReadMessages CallControl Faxes..."
    token_type: str  # "Bearer"
    owner_id: str  # alphanumeric


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def ringcentral_call_subscription_event_receiver_view(request, practice_telecom_id=None, call_subscription_id=None):

    # When creating the webhook, ringcentral expects the validation token it sends to be sent back to verify the endpoint
    if "Validation-Token" in request.headers:
        response = HttpResponse(status=200)
        response.headers["Validation-Token"] = request.headers["Validation-Token"]
        response.headers["Content-type"] = "application/json"
        return response

    # validate practice telecom exists and is active
    practice_telecom: PracticeTelecom = get_object_or_404(
        PracticeTelecom.objects.select_related("practice", "voip_provider"), pk=practice_telecom_id, practice__active=True
    )
    log.info(f"Validated practice telecom with practice_telecom_id: '{practice_telecom_id}'")

    # Grab Practice and VOIP Provider for downstream processing
    practice = practice_telecom.practice
    practice_id = practice_telecom.practice.id

    if not practice:
        message = f"No valid practice found for practice_telecom_id = '{practice_telecom_id}'"
        log.exception(f"{message}. This should not be possible since this is a non-nullable relationship.")
        return Response(status=status.HTTP_404_NOT_FOUND, data={"message": message})

    voip_provider = practice_telecom.voip_provider
    if not voip_provider:
        message = (
            f"No valid voip_provider found for this practice '{practice_id}'. A voip_provider must be set up first in order to receive subscription events."
        )
        log.exception(f"{message}. Practice is not set up properly and needs a voip_provider. Somehow a subscription was set up and events are being received!")
        return Response(status=status.HTTP_404_NOT_FOUND, data={"message": message})
    voip_provider_id = voip_provider.id

    log.info(f"Validating call_subscription for: call_subscription_id: '{call_subscription_id}'")
    # validate an active subscription exists and is associated with the practice telecom, not referenced later, we just need the check
    get_object_or_404(RingCentralCallSubscription, pk=call_subscription_id, active=True)
    log.info(f"Validated call_subscription for: call_subscription_id: '{call_subscription_id}'")

    try:
        req = json.loads(request.body)
        session = req["body"]
        status_code = session["parties"][0]["status"]["code"]
    except (json.JSONDecodeError, KeyError):
        return HttpResponse(status=406)

    RingCentralSessionEvent.objects.create(
        full_session_event=session,
        sequence=session["sequence"],
        session_id=session["sessionId"],
        telephony_session_id=session["telephonySessionId"],
        server_id=session["serverId"],
        event_time=session["eventTime"],
        to_name=session["parties"][0]["to"].get("name"),
        to_extension_id=session["parties"][0]["to"].get("extensionId"),
        to_phone_number=session["parties"][0]["to"].get("phoneNumber"),
        from_name=session["parties"][0]["from"].get("name"),
        from_extension_id=session["parties"][0]["from"].get("extensionId"),
        from_phone_number=session["parties"][0]["from"].get("phoneNumber"),
        muted=session["parties"][0]["muted"],
        status_rcc=session["parties"][0]["status"].get("rcc"),
        status_code=session["parties"][0]["status"].get("code"),
        status_reason=session["parties"][0]["status"].get("reason"),
        account_id=session["parties"][0]["accountId"],
        direction=session["parties"][0]["direction"],
        missed_call=session["parties"][0]["missedCall"],
        stand_alone=session["parties"][0]["standAlone"],
    )

    # TODO: still under investigation on if this is the proper disconnect event to check
    if status_code == "Disconnected":
        #
        # PROCESSING
        #

        try:
            log.info(
                f"[RingCentral] Publishing call disconnected events for: telephony_session_id: '{session['telephonySessionId']}' and account_id: '{session['parties'][0]['accountId']}'"
            )
            publish_call_create_call_record_event(
                ringcentral_telephony_session_id=session["telephonySessionId"],
                ringcentral_session_id=session["sessionId"],
                practice_id=practice_id,
                voip_provider_id=voip_provider_id,
            )
            log.info(
                f"Published create call events for: telephony_session_id: '{session['telephonySessionId']}' and account_id: '{session['parties'][0]['accountId']}'"
            )
        except PermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            log.exception(message)
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

    return HttpResponse(status=200)


# Note: this is not used but will be kept for future reference
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        default_handler = self._login_to_ringcentral
        grant_handler_map = {
            "password": default_handler,
        }

        ringcentral_access_token_response = None
        try:
            grant_type = request.data.get("grant_type")
            handler = grant_handler_map.get(grant_type, default_handler)
            ringcentral_access_token_response = handler(request)

            return ringcentral_access_token_response
        except APIException as api_exception:
            # pass it through
            raise api_exception
        except Exception as e:
            # unexpected exceptions 500 internal server error
            log.exception(e)
            return Response(status=500, data={"detail": "Server Error"})

    def _login_to_ringcentral(self, request: HttpRequest):

        username = request.data.get("username")
        password = request.data.get("password")
        ringcentral_api_client = self._get_ringcentral_client_secret(username, password)

        log.info(f"User is attempting login. username='{username}'.")

        if not (username and password):
            log.info(f"Bad Request detected for login. Missing one or more required fields.")
            raise ParseError(f"Bad Request detected for login. Missing one or more required fields.")

        rcsdk = SDK(ringcentral_api_client.client_id, ringcentral_api_client.client_secret, ringcentral_api_client.api_url)
        platform = rcsdk.platform()

        try:
            platform.login(username, "", password)
        except Exception as e:
            raise PermissionDenied()

        response_json = platform.auth().data()
        ringcentral_auth_token = RingCentralAuthToken.parse_obj(response_json)
        self._setup_user_and_save_activity(username, ringcentral_auth_token)

        return Response(status=200, data=response_json)

    def _get_ringcentral_client_secret(self, username, password):
        ringcentral_api_credentials = RingCentralAPICredentials.objects.get(username=username, password=password)
        return ringcentral_api_credentials

    def _setup_user_and_save_activity(self, username, ringcentral_auth_token: RingCentralAuthToken) -> None:
        now = timezone.now()

        with transaction.atomic():
            user, user_created = setup_user(
                username=username,
                name=username,
                email=username,
                domain="",
                login_time=now,
            )
            save_user_activity_and_token(
                access_token=ringcentral_auth_token.access_token,
                refresh_token=ringcentral_auth_token.refresh_token,
                login_time=now,
                expires_in_seconds=ringcentral_auth_token.expires_in,
                user=user,
            )

            if user_created:
                create_user_telecom(user)
                practice, _ = setup_practice("")
                create_agent(user, practice)


class AdminRingCentralAPICredentialsViewSet(viewsets.ModelViewSet):
    queryset = RingCentralAPICredentials.objects.all().order_by("voip_provider", "active", "-created_at")
    serializer_class = AdminRingCentralAPICredentialsSerializer

    filterset_fields = ["voip_provider", "active"]


class RingCentralCallLegViewSet(viewsets.ModelViewSet):
    queryset = RingCentralCallLeg.objects.all()
    serializer_class = RingCentralCallLegSerializer
