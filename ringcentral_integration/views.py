import json

from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import viewsets
from .models import (
    RingCentralSessionEvent,
)

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny


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
        sequence = session['sequence'],
        session_id = session['sessionId'],
        telephony_session_id = session['telephonySessionId'],
        server_id = session['serverId'],
        event_time = session['eventTime'],
        parties = session['parties'],

    )

    return HttpResponse(status=200)
