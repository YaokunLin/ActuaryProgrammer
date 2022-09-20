import json
import logging

from django.shortcuts import render
from django.db import transaction
from django.http import HttpResponse, HttpRequest
from rest_framework import viewsets
from .models import (
    RingCentralSessionEvent,
    RingCentralAPICredentials
)
from pydantic import BaseModel
from ringcentral import SDK
from ringcentral_integration.publishers import publish_call_discounted_event
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    ParseError,
    PermissionDenied,
)
from core.setup_user_and_practice import (
    create_agent,
    create_user_telecom,
    save_user_activity_and_token,
    setup_practice,
    setup_user
)

from google.api_core.exceptions import PermissionDenied

# Get an instance of a logger
log = logging.getLogger(__name__)

class RingCentralAuthToken(BaseModel):
    access_token: str  # alphanumberic
    expires_in: int  # e.g. "3600"
    refresh_token: str  # alphanumberic
    refresh_token_expires_in: int # "604800"
    refresh_token_expire_time: int # "1664289200.5082414"
    scope: str  # e.g. "ReadMessages CallControl Faxes..."
    token_type: str  # "Bearer"
    owner_id: str # alphanumberic


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook(request):

    # When creating the webhook, ringcentral expects the validation token it sends to be sent back to verify the endpoint
    if('Validation-Token' in request.headers):
        response = HttpResponse(status=200)
        response.headers['Validation-Token'] = request.headers['Validation-Token']
        response.headers['Content-type'] = 'application/json'
        return response
    
    try:
        req = json.loads(request.body)
        session = req['body']
        status_code = session['parties'][0]['status']['code']
    except (json.JSONDecodeError, KeyError):
        return HttpResponse(status=406)

    RingCentralSessionEvent.objects.create(
        full_session_event = session,
        sequence = session['sequence'],
        session_id = session['sessionId'],
        telephony_session_id = session['telephonySessionId'],
        server_id = session['serverId'],
        event_time = session['eventTime'],
        to_name= session['parties'][0]['to'].get('name'),
        to_extension_id= session['parties'][0]['to'].get('extensionId'),
        to_phone_number= session['parties'][0]['to'].get('phoneNumber'),
        from_name= session['parties'][0]['from'].get('name'),
        from_extension_id= session['parties'][0]['from'].get('extensionId'),
        from_phone_number= session['parties'][0]['from'].get('phoneNumber'),
        muted= session['parties'][0]['muted'],
        status_rcc= session['parties'][0]['status'].get('rcc'),
        status_code= session['parties'][0]['status'].get('code'),
        status_reason= session['parties'][0]['status'].get('reason'),
        account_id= session['parties'][0]['accountId'],
        direction= session['parties'][0]['direction'],
        missed_call= session['parties'][0]['missedCall'],
        stand_alone= session['parties'][0]['standAlone'],
    )

    if status_code == 'Disconnected' and session['parties'][0]['status'].get('reason') is None:
        #
        # PROCESSING
        #

        try:
            log.info(f"[RingCentral] Publishing call disconnected events for: telephony_session_id: '{session['telephonySessionId']}' and account_id: '{session['parties'][0]['accountId']}'")
            publish_call_discounted_event(
                ringcentral_telephony_session_id=session['telephonySessionId'], practice_id=0, ringcentral_account_id=session['parties'][0]['accountId']
            )
            log.info(f"Published leg b ready events for: telephony_session_id: '{session['telephonySessionId']}' and account_id: '{session['parties'][0]['accountId']}'")
        except PermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            log.exception(message)
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

    return HttpResponse(status=200)



class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        default_handler = self._login_to_ringcentral
        grant_handler_map = {
            "password": default_handler,
        }

        ringcentral_access_token_response = None
        print(request)
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


    def _login_to_ringcentral(
            self,
            request: HttpRequest
        ):

        username = request.data.get("username")
        password = request.data.get("password")
        ringcentral_account_id = request.data.get("ringcentral_account_id")
        ringcentral_api_client = self._get_ringcentral_client_secret(username, ringcentral_account_id)

        log.info(f"User is attempting login. username='{username}'.")

        if not (username and password):
            log.info(f"Bad Request detected for login. Missing one or more required fields.")
            raise ParseError()

        rcsdk = SDK( ringcentral_account_id,
             ringcentral_api_client.client_secret,
             ringcentral_api_client.api_url )
        platform = rcsdk.platform()

        try:
            platform.login(username, '', password)
        except Exception as e:
            raise PermissionDenied()

        response_json = platform.auth().data()
        ringcentral_auth_token = RingCentralAuthToken.parse_obj(response_json)
        self._setup_user_and_save_activity(username, ringcentral_auth_token)

        return Response(status=200, data=response_json)

    def _get_ringcentral_client_secret(self, username, ringcentral_account_id):
        ringcentral_api_credentials = RingCentralAPICredentials.objects.get(username=username, client_id=ringcentral_account_id)
        return ringcentral_api_credentials
    
    def _setup_user_and_save_activity(self, username, ringcentral_auth_token: RingCentralAuthToken) -> None:
        now = timezone.now()

        with transaction.atomic():
            user, user_created = setup_user(
                username=username,
                name=username,
                email=username,
                domain='',
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
                practice, _ = setup_practice('')
                create_agent(user, practice)
