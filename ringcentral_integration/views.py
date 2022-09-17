import json
import logging

from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import viewsets
from .models import (
    RingCentralSessionEvent,
)

from ringcentral_integration.publishers import publish_call_discounted_event

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from google.api_core.exceptions import PermissionDenied

# Get an instance of a logger
log = logging.getLogger(__name__)


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
