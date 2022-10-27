import base64
from contextlib import suppress
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Set

import dateutil.parser
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from rest_framework.decorators import api_view, authentication_classes, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from calls.field_choices import CallConnectionTypes, CallDirectionTypes, SupportedAudioMimeTypes, CallAudioFileStatusTypes
from calls.models import Call, CallPartial, CallAudioPartial
from core.field_choices import VoipProviderIntegrationTypes
from core.validation import get_validated_practice_telecom
from jive_integration.jive_client.client import JiveClient, Line
from jive_integration.publishers import publish_leg_b_ready_event
from jive_integration.serializers import JiveSubscriptionEventExtractSerializer
from jive_integration.models import JiveConnection, JiveLine, JiveChannel, JiveSession
from jive_integration.utils import get_call_id_from_previous_announce_event

# Get an instance of a logger
log = logging.getLogger(__name__)

US_TELEPHONE_NUMBER_DIGIT_LENGTH = 10


def generate_redirect_uri(request):
    return request.build_absolute_uri(reverse("jive_integration:authentication-callback"))


def generate_jive_callback_url(
    request: Request,
    jive_authorization_url: str = settings.JIVE_AUTHORIZATION_URL,
    jive_client_id: str = settings.JIVE_CLIENT_ID,
):
    return f"{jive_authorization_url}?client_id={jive_client_id}&response_type=code&redirect_uri={generate_redirect_uri(request)}"


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook(request):
    # https://api.jive.com/call-reports/v1/recordings/4428338e-826b-40af-b4a0-d01a2010f525?organizationId=af93983c-ec29-4aca-8516-b8ab36b587d1

    # TODO: validate using print(line.session.channel.signature)
    #
    log.info(f"Jive webhook: Headers: '{request.headers}' POST body '{request.body}'")

    #
    # VALIDATION
    #

    try:
        req = json.loads(request.body)
        content = json.loads(req["content"])
    except (json.JSONDecodeError, KeyError):
        return HttpResponse(status=406)

    end_time: datetime = dateutil.parser.isoparser().isoparse(req["timestamp"])
    entity_id = content.get("entityId")
    subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=content)
    subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()
    subscription_event_data = subscription_event_serializer.validated_data

    if not subscription_event_serializer_is_valid:
        log.exception(f"Jive: Error from subscription_event_serializer validation from entity_id {entity_id}: {subscription_event_serializer.errors}")
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": subscription_event_serializer.errors})

    direction: CallDirectionTypes
    if content["data"]["direction"] == "recipient":
        direction = CallDirectionTypes.INBOUND
    else:
        direction = CallDirectionTypes.OUTBOUND

    log.info(f"Jive: Getting JiveLine with subId='{content['subId']}' and originatorOrganizationId='{content['data']['originatorOrganizationId']}'")
    line: JiveLine = JiveLine.objects.get(source_jive_id=content["subId"], source_organization_jive_id=content["data"]["originatorOrganizationId"])
    log.info(f"Jive: Got JiveLine with subId='{content['subId']}' and originatorOrganizationId='{content['data']['originatorOrganizationId']}'")

    voip_provider_id = line.session.channel.connection.practice_telecom.voip_provider_id

    # TODO: content["type"] should be a field choice type - will check these when we have documentation for understanding the options
    if content["type"] == "announce":
        log.info("Jive: Received jive announce event.")
        start_time: datetime = dateutil.parser.isoparser().isoparse(req["timestamp"])
        log.info(f"Jive: Creating Peerlogic Call object with start_time='{start_time}'.")
        callee_number = content["data"]["callee"]["number"]
        caller_number = content["data"]["caller"]["number"]
        callee_key = "sip_callee_number"
        caller_key = "sip_caller_number"
        if len(callee_number) != US_TELEPHONE_NUMBER_DIGIT_LENGTH:
            callee_key = "sip_callee_extension"
        if len(caller_number) != US_TELEPHONE_NUMBER_DIGIT_LENGTH:
            caller_key = "sip_caller_extension"

        call_fields = {
            "practice": line.session.channel.connection.practice_telecom.practice,
            "call_start_time": start_time,
            "duration_seconds": timedelta(seconds=0),
            "call_direction": direction,
            callee_key: callee_number,  # TODO: get true TN number called from in downstream subscribing cloud functions
            "sip_callee_name": content["data"]["callee"]["name"],
            caller_key: caller_number,  # TODO: get true TN number called from in downstream subscribing cloud functions
            "sip_caller_name": content["data"]["caller"]["name"],
            "checked_voicemail": False,  # TODO: determine value in downstream subscribing cloud functions
            "went_to_voicemail": False,  # TODO: determine value in downstream subscribing cloud functions
        }

        peerlogic_call = Call.objects.create(**call_fields)
        log.info(f"Jive: Created Peerlogic Call object with id='{peerlogic_call.id}'.")

        subscription_event_data.update({"peerlogic_call_id": peerlogic_call.id})
        subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=subscription_event_data)
        subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()

    elif content["type"] == "replace":
        log.info("Jive: Received jive replace event.")
        call_id = get_call_id_from_previous_announce_event(content["oldId"])
        subscription_event_data.update({"peerlogic_call_id": call_id})
        subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=subscription_event_data)
        subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()

    elif content["type"] == "withdraw":
        log.info("Jive: Received jive withdraw event.")

        call_id = get_call_id_from_previous_announce_event(content["entityId"])
        log.info(f"Jive: Call ID is {call_id}")
        subscription_event_data.update({"peerlogic_call_id": call_id})
        subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=subscription_event_data)
        subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()

        recording_count = len(content["data"]["recordings"])
        log.info(f"Jive: Found {recording_count} recordings.")

        if recording_count == 0:
            # TODO: call Jive API to see if there is a corresponding Voicemail
            log.info("Jive: Updating Peerlogic call end time and duration.")
            peerlogic_call = Call.objects.get(pk=call_id)
            peerlogic_call.call_end_time = end_time
            peerlogic_call.duration_seconds = peerlogic_call.call_end_time - peerlogic_call.call_start_time
            peerlogic_call.call_connection = CallConnectionTypes.MISSED
            peerlogic_call.save()
            log.info(
                f"Jive: Updated Peerlogic call with the following fields: peerlogic_call.call_connection='{peerlogic_call.call_connection}', peerlogic_call.call_end_time='{peerlogic_call.call_end_time}', peerlogic_call.duration_seconds='{peerlogic_call.duration_seconds}'"
            )

        recordings = []
        for recording in content["data"]["recordings"]:
            filename_encoded = recording["filename"]
            filename = base64.b64decode(recording["filename"]).decode("utf-8")
            ord = dateutil.parser.isoparser().isoparse(filename.split("~", maxsplit=1)[0].split("/")[-1])

            recordings.append([ord, filename, filename_encoded])

        recordings = sorted(recordings, key=lambda r: r[0])

        for recording in recordings:
            ord = recording[0]
            filename = recording[1]
            filename_encoded = recording[2]

            log.info("Jive: Updating Peerlogic call end time and duration.")
            peerlogic_call = Call.objects.get(pk=call_id)
            peerlogic_call.call_end_time = end_time
            peerlogic_call.duration_seconds = peerlogic_call.call_end_time - peerlogic_call.call_start_time
            peerlogic_call.call_connection = CallConnectionTypes.CONNECTED
            peerlogic_call.save()
            log.info(
                f"Jive: Updated Peerlogic call with the following fields: peerlogic_call.call_connection='{peerlogic_call.call_connection}', peerlogic_call.call_end_time='{peerlogic_call.call_end_time}', peerlogic_call.duration_seconds='{peerlogic_call.duration_seconds}'"
            )

            log.info(
                f"Jive: Creating Peerlogic CallPartial with peerlogic_call.id='{peerlogic_call.id}',  time_interaction_started='{peerlogic_call.call_start_time}' and time_interaction_ended='{ord}'."
            )
            # TODO: Get previous call partials for call and see if we need to update the time_interaction started. We only get end times.
            # Double-check with transfers
            cp = CallPartial.objects.create(call=peerlogic_call, time_interaction_started=peerlogic_call.call_start_time, time_interaction_ended=end_time)
            log.info(
                f"Jive: Created Peerlogic CallPartial with cp.id='{cp.id}', peerlogic_call.id='{peerlogic_call.id}', time_interaction_started='{peerlogic_call.call_start_time}' and entime_interaction_endedd_time='{end_time}'."
            )

            subscription_event_data.update({"peerlogic_call_partial_id": cp.id})
            subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=subscription_event_data)
            subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()

            publish_leg_b_ready_event(
                jive_call_subscription_id=content["subId"],
                voip_provider_id=voip_provider_id,
                event={
                    "jive_entity_id": content["entityId"],
                    "peerlogic_call_id": peerlogic_call.id,
                    "peerlogic_call_partial_id": cp.id,
                    "filename": filename_encoded,
                },
            )

    subscription_event_serializer.save()

    return HttpResponse(status=202)


@api_view(["GET"])
@renderer_classes([])
def authentication_connect(request: Request):
    """
    This view returns a redirect to initialize the connect flow with the Jive API.  Users will be redirected to Jive's
    application to confirm access to Peerlogic's systems.

    https://developer.goto.com/guides/Authentication/03_HOW_accessToken/
    https://developer.goto.com/Authentication/#section/Authorization-Flows/Authorization-Code-Grant
    Scroll to 1. Redirect the user to our authorization URL
    """
    return HttpResponseRedirect(redirect_to=generate_jive_callback_url(request))


@api_view(["GET"])
def authentication_connect_url(request: Request):
    """
    This view returns the url to initialize the connect flow with the Jive API.  This is informational to understand what url
    a client must call to present the user Jive's application to confim access to Peerlogic's systems

    https://developer.goto.com/guides/Authentication/03_HOW_accessToken/
    https://developer.goto.com/Authentication/#section/Authorization-Flows/Authorization-Code-Grant
    Scroll to 1. Redirect the user to our authorization URL
    """
    return Response(status=200, data={"url": generate_jive_callback_url(request)})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def authentication_callback(request: Request):
    """
    This view will exchange the given authentication code for an access token from the Jive authentication API.
    Refresh tokens are stored on `JiveConnection` objects and linked to a practice.  If a connection object is not
    found for the given user one will be created.

    https://developer.goto.com/guides/Authentication/03_HOW_accessToken/
    """
    authorization_code: Optional[str] = request.query_params.get("code")
    if not authorization_code:
        return Response(status=404, data={"errors": {"code": "Missing from query parameters."}})

    # Exchange the authorization code for an access token
    log.info("Instantiating JiveClient.")
    jive: JiveClient = JiveClient(client_id=settings.JIVE_CLIENT_ID, client_secret=settings.JIVE_CLIENT_SECRET)
    log.info("Instantiated JiveClient.")

    log.info("Exchanging authorization code for an access code.")
    jive.exchange_code(authorization_code, generate_redirect_uri(request))
    log.info("Exchanged authorization code for an access code.")

    principal = jive.principal  # this is the email associated with user

    if not principal:
        return Response(status=404, data={"errors": {"principal": "Missing from exchange authorization code for access token response."}})

    connection: JiveConnection = None

    with suppress(JiveConnection.DoesNotExist):
        connection = JiveConnection.objects.get(practice_telecom__practice__agent__user__email=principal)

    if not connection:
        # TODO: deal with users with multiple practices (Organizations ACL)
        practice_telecom, errors = get_validated_practice_telecom(voip_provider__integration_type=VoipProviderIntegrationTypes.JIVE, email=principal)
        if not practice_telecom:
            log.info(f"No practice telecom has set up for this Jive customer with user email or principal='{principal}'")
            return Response(status=404, data=errors)
        connection = JiveConnection(practice_telecom=practice_telecom)

    connection.refresh_token = jive.refresh_token

    connection.save()

    return HttpResponse(status=204)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def cron(request):
    """
    Jive event subscriptions must be refreshed every week. Additionally, there is no push event when a line is added
    or removed from an account.   This endpoint will sync the lines from jive for each active connection.  Connections
    are prioritized by the longest interval since the last sync.  Any stale or invalid channels will be garbage
    collected though the records may remain in the database for a period to ensure any latent events sent to the
    webhook receiver will still be routed correctly.
    """
    log.info("Jive: syncing jive lines and subscriptions")

    # to avoid timeouts we want to complete execution in 30s
    deadline = datetime.now() + timedelta(seconds=60)

    # cleanup any expired channels, this will cascade to sessions and lines
    JiveChannel.objects.filter(expires_at__lt=timezone.now()).delete()

    # for each user connection
    for connection in JiveConnection.objects.filter(active=True).order_by("-last_sync"):
        log.info(f"Jive: found connection: {connection}")
        jive: JiveClient = JiveClient(client_id=settings.JIVE_CLIENT_ID, client_secret=settings.JIVE_CLIENT_SECRET, refresh_token=connection.refresh_token)
        if deadline < datetime.now():
            return HttpResponse(status=204)

        # find any channels about to expire in the next few hours and refresh them

        # TODO: use JiveChannel.objects.filter(expires_at__lt=timezone.now() - timedelta(hours=3))
        # Dependencies:
        # * cron cloud run deployed
        # FURTHER TODO: make the 3 hours configurable via env var / Secret Manager
        for channel in JiveChannel.objects.all():
            log.info(f"Jive: found channel: {channel}")
            # if a channel refresh fails we mark it as inactive
            try:
                log.info(f"Jive: refreshing channel: {channel}")
                jive.refresh_channel_lifetime(channel)
            except:
                log.info(f"Jive: failed to refresh channel {channel.id}, marking as inactive")
                channel.active = False
                channel.save()

        # get the current lines with an active channel for this connection
        line_results = JiveLine.objects.filter(session__channel__connection=connection, session__channel__active=True).values_list(
            "source_jive_id", "source_organization_jive_id"
        )
        current_lines = {Line(r[0], r[1]) for r in line_results}
        external_lines: Set[Line] = set(jive.list_lines())

        # compute new lines
        add_lines = external_lines - current_lines
        remove_lines = current_lines - external_lines

        log.info(f"Jive: found {len(add_lines)} new lines and {len(remove_lines)} invalid lines for connection {connection.id}.")

        # delete the removed lines
        JiveLine.objects.filter(source_jive_id__in=remove_lines).delete()

        if add_lines:
            # get the latest active channel for this connection
            channel = JiveChannel.objects.filter(connection=connection, active=True, expires_at__gt=timezone.now()).order_by("-expires_at").first()

            # if no channels are found create one
            if not channel:
                log.info(f"Jive: no active webhook channel found for connection='{connection}', creating one.")
                webhook_url = request.build_absolute_uri(reverse("jive_integration:webhook-receiver"))

                # Jive will only accept a https url so we always replace it, the only case where this would not
                # be an https url is a development environment.
                webhook_url = webhook_url.replace("http://", "https://")

                channel = jive.create_webhook_channel(connection=connection, webhook_url=webhook_url)
                log.info(f"Jive: created channel='{channel}' for connection='{connection}'.")
                # TODO: better error handling from above client call

            # get the latest session for this channel
            session = JiveSession.objects.filter(channel=channel).order_by("-channel__expires_at").first()

            # if no session is found create one
            if not session:
                log.info(f"Jive: no session found for channel='{channel}', creating one.")
                session = jive.create_session(channel=channel)
                log.info(f"Jive: created session='{session}' for channel='{channel}'.")
                # TODO: better error handling from above client call

            # subscribe to the new lines
            log.info(f"Jive: subscribing to {add_lines} with session='{session}'")
            jive.create_session_dialog_subscription(session, *add_lines)
            log.info(f"Jive: subscribed to {add_lines} with session='{session}'")
            # TODO: better error handling from above client call

        # record sync event to ensure all connections get a chance to be synced
        # TODO: determine if we should not update this when some channel, session, line or connection has an error
        # It's led to issues understanding staleness of connections because it's ALWAYS updated.
        connection.last_sync = timezone.now()
        connection.save()

    return HttpResponse(status=202)
