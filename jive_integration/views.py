import base64
from contextlib import suppress
import functools
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Set

import dateutil.parser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from rest_framework.decorators import api_view, authentication_classes, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from calls.field_choices import CallDirectionTypes, SupportedAudioMimeTypes, CallAudioFileStatusTypes
from calls.models import Call, CallPartial, CallAudioPartial
from calls.publishers import publish_call_audio_partial_saved
from core.field_choices import VoipProviderIntegrationTypes
from core.models import PracticeTelecom
from core.validation import get_validated_practice_telecom
from jive_integration.jive_client.client import JiveClient, Line
from jive_integration.models import JiveConnection, JiveLine, JiveChannel, JiveSession, JiveCallPartial

# Get an instance of a logger
log = logging.getLogger(__name__)


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

    # todo validate  print(line.session.channel.signature)
    #

    try:
        req = json.loads(request.body)
        content = json.loads(req["content"])
    except (json.JSONDecodeError, KeyError):
        return HttpResponse(status=406)

    # TODO:
    # 1. Figure out why S3 retrieval isn't working
    # 2. Extract raw subscription event (get rid of JiveCallPartial)
    # 3. Update or create CDR / Call log if needed
    # 4. Create Peerlogic call on announce
    # 5. Update Peerlogic call on withdraw
    # 6. Verify Call Partial exists
    # 7. Update or Create Call Audio Partial

    # THEN:
    # Re-do all of this with the Pub/sub and Cloud Function architecture
    # instead of abusing this webhook and losing everything if something fails or we can't scale this endpoint with the traffic.

    # We only care about hangup events because the recording will be ready
    if content["type"] == "announce":
        log.info("Received jive announce event.")
        log.info(f"Creating JiveCallPartial with start time of timestamp='{req['timestamp']}' and entityId='{content['entityId']}'")
        JiveCallPartial.objects.create(start_time=dateutil.parser.isoparser().isoparse(req["timestamp"]), source_jive_id=content["entityId"])
    elif content["type"] == "replace":
        log.info("Received jive replace event.")
        log.info(f"Filtering JiveCallPartial with oldId='{content['oldId']}' and newId='{content['newId']}'")
        JiveCallPartial.objects.filter(source_jive_id=content["oldId"]).update(source_jive_id=content["newId"])
    elif content["type"] == "withdraw":
        log.info("Received jive withdraw event.")
        log.info(f"Getting JiveLine with subId='{content['subId']}' and originatorOrganizationId='{content['data']['originatorOrganizationId']}'")
        line: JiveLine = JiveLine.objects.get(source_jive_id=content["subId"], source_organization_jive_id=content["data"]["originatorOrganizationId"])
        log.info(f"Got JiveLine with subId='{content['subId']}' and originatorOrganizationId='{content['data']['originatorOrganizationId']}'")

        try:
            log.info(f"Getting JiveCallPartial with entityId='{content['entityId']}'")
            part = JiveCallPartial.objects.get(source_jive_id=content["entityId"])
            log.info(f"Got JiveCallPartial with entityId='{content['entityId']}'")
        except ObjectDoesNotExist:  # it is possible for duplicate withdraw messages to be sent, so we ignore duplicates
            return HttpResponse(status=202)

        start_time: datetime = part.start_time
        end_time: datetime = dateutil.parser.isoparser().isoparse(req["timestamp"])

        direction: CallDirectionTypes
        if content["data"]["direction"] == "recipient":
            direction = CallDirectionTypes.INBOUND
        else:
            direction = CallDirectionTypes.OUTBOUND

        print("webhook content")
        print(content)

        # TODO: get sip_caller_number from previous extracts. See below for withdraw events:
        # Inbound
        # {
        # 'type': 'withdraw',
        # 'subId': 'cc23a545-9594-4f5f-b59d-d9022aba6ecb',
        # 'entityId': '625957634',
        # 'data': {
        # 'legId': '15c2c70d-b9bb-4128-aef3-b65bd4f8d5a6',
        # 'created': 1663623167457,
        # 'participant': '31hyS3uK0ODIr0QXf2jUF9VyUeBjp0',
        # 'callee': {'name': 'Research Development', 'number': '1000'},
        # 'caller': {'name': 'WIRELESS CALLER', 'number': '4806525408'},
        # 'direction': 'recipient', 'state': 'HUNGUP', 'ani': '+15203759246 <+15203759246>',
        # 'recordings': [
        #   {'filename': 'MjAyMi0wOS0xOVQxNTMyNDd+Y2FsbH4rMTQ4MDY1MjU0MDh+KzE1MjAzNzU5MjQ2fjQ5ZTBmZWQxLTQ3OWQtNDYzZi04OWI3LWI0ODFkZTkwY2UwOS53YXY='
        # }],
        # 'isClickToCall': False, 'originatorId': '80793972-282f-439c-9cc1-29ff0446eac6', 'originatorOrganizationId': 'af93983c-ec29-4aca-8516-b8ab36b587d1'
        # }
        # }

        # Outbound
        # {
        # 'type': 'withdraw', 'subId': 'cc23a545-9594-4f5f-b59d-d9022aba6ecb',
        # 'entityId': '627872218',
        # 'data': {
        # 'legId': '0ea9e26b-df04-43fb-921c-bdd89bbe86b8',
        # 'created': 1663623816968,
        # 'participant': '31hyS3uK0ODIr0QXf2jUF9VyUeBjp0',
        # 'callee': {'name': 'Unknown', 'number': '4806525408'},
        # 'caller': {'name': 'Research Development', 'number': '1000'},
        # 'direction': 'initiator', 'state': 'HUNGUP',
        # 'recordings': [{'filename': 'MjAyMi0wOS0xOVQxNTQzMzZ+Y2FsbH4xMDAwfjQ4MDY1MjU0MDh+MDkwOGFiYjgtMDRmZS00NWJiLTlmMTItYzJhYzc1NDc1ZTNlLndhdg=='}],
        # 'isClickToCall': False, 'originatorId': '0ea9e26b-df04-43fb-921c-bdd89bbe86b8', 'originatorOrganizationId': 'af93983c-ec29-4aca-8516-b8ab36b587d1'
        #   }
        # }

        # If Direction is inbound:
        # sip_callee_extension = data['callee']['number']
        # sip_callee_number = f"+1{data['ani'].split(' ')[0]}"
        # sip_caller_extension = None
        # sip_caller_number = f"+1{data['caller']['number'].split(' ')[0]}"

        # If Direction is outbound:
        # sip_callee_extension = None
        # sip_callee_number = f"+1{data['callee']['number']}"
        # sip_caller_extension = data['caller']['number']
        # sip_caller_number = None (Can't get it from this event)

        # TODO: Fix, this is creating 2 - 3 duplicate Peerlogic calls per actual call taking place.
        log.info(f"Creating Peerlogic Call object with start_time='{start_time}'.")
        call = Call.objects.create(
            practice=line.session.channel.connection.practice_telecom.practice,
            call_start_time=start_time,
            call_end_time=end_time,
            duration_seconds=end_time - start_time,
            call_direction=direction,
            sip_caller_number=content["data"]["caller"]["name"],
            sip_caller_name=content["data"]["caller"]["number"],
            sip_callee_number=content["data"]["callee"]["number"],
            sip_callee_name=content["data"]["callee"]["name"],
        )
        log.info(f"Created Peerlogic Call object with id='{call.id}'.")

        log.info(f"Retrieving recordings from jive.")
        recordings = []
        for recording in content["data"]["recordings"]:
            filename = base64.b64decode(recording["filename"]).decode("utf-8")
            ord = dateutil.parser.isoparser().isoparse(filename.split("~", maxsplit=1)[0].split("/")[-1])

            recordings.append([ord, filename])

        recordings = sorted(recordings, key=lambda r: r[0])

        for recording in recordings:
            ord = recording[0]
            filename = recording[1]

            log.info(f"Creating Peerlogic CallPartial with call.id='{call.id}', time_interaction_started='{ord}' and time_interaction_ended='{ord}'.")
            cp = CallPartial.objects.create(
                call=call, time_interaction_started=ord, time_interaction_ended=ord
            )  # TODO: fix end_time? This doesn't seem right for end_time to ord
            log.info(
                f"Created Peerlogic CallPartial with cp.id='{cp.id}', call.id='{call.id}', time_interaction_started='{ord}' and entime_interaction_endedd_time='{ord}'."
            )

            log.info(f"Creating Peerlogic CallAudioPartial with cp.id='{cp.id}', call.id='{call.id}'")
            cap = CallAudioPartial.objects.create(
                call_partial=cp, mime_type=SupportedAudioMimeTypes.AUDIO_WAV, status=CallAudioFileStatusTypes.RETRIEVAL_FROM_PROVIDER_IN_PROGRESS
            )
            log.info(
                f"Created Peerlogic CallAudioPartial with cap.id='{cap.id}', cp.id='{cp.id}', call.id='{call.id}', start_time='{ord}' and end_time='{ord}'."
            )

            log.info(
                f"Writing Jive Recording to S3 bucket='{settings.JIVE_BUCKET_NAME}' for Peerlogic CallAudioPartial with cap.id='{cap.id}', call.id='{call.id}'"
            )
            with io.BytesIO() as buf:
                settings.S3_CLIENT.download_fileobj(settings.JIVE_BUCKET_NAME, filename, buf)
                cap.put_file(buf)
            log.info(
                f"Wrote Jive Recording to S3 bucket='{settings.JIVE_BUCKET_NAME}' for Peerlogic CallAudioPartial with cap.id='{cap.id}', call.id='{call.id}'"
            )

            publish_call_audio_partial_saved(call_id=call.id, partial_id=cp.id, audio_partial_id=cap.id)

        part.delete()

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
    logging.info("syncing jive lines and subscriptions")

    # to avoid timeouts we want to complete execution in 30s
    deadline = datetime.now() + timedelta(seconds=60)

    # cleanup any expired channels, this will cascade to sessions and lines
    JiveChannel.objects.filter(expires_at__lt=timezone.now()).delete()

    # for each user connection
    for connection in JiveConnection.objects.filter(active=True).order_by("-last_sync"):
        jive: JiveClient = JiveClient(client_id=settings.JIVE_CLIENT_ID, client_secret=settings.JIVE_CLIENT_SECRET, refresh_token=connection.refresh_token)
        if deadline < datetime.now():
            return HttpResponse(status=204)

        # find any channels about to expire in the next few hours and refresh them
        for channel in JiveChannel.objects.filter(expires_at__lt=timezone.now() - timedelta(hours=3)):
            # if a channel refresh fails we mark it as inactive
            try:
                jive.refresh_channel_lifetime(channel)
            except:
                logging.info(f"failed to refresh channel {channel.id}, marking as inactive")
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

        logging.info(f"found {len(add_lines)} new lines and {len(remove_lines)} invalid lines for connection {connection.id}")

        # delete the removed lines
        JiveLine.objects.filter(source_jive_id__in=remove_lines).delete()

        if add_lines:
            # get the latest active channel for this connection
            channel = JiveChannel.objects.filter(connection=connection, active=True, expires_at__gt=timezone.now()).order_by("-expires_at").first()

            # if no channels are found create one
            if not channel:
                webhook_url = request.build_absolute_uri(reverse("jive_integration:webhook-receiver"))

                # Jive will only accept a https url so we always replace it, the only case where this would not
                # be an https url is a development environment.
                webhook_url = webhook_url.replace("http://", "https://")

                channel = jive.create_webhook_channel(connection=connection, webhook_url=webhook_url)

            # get the latest session for this channel
            session = JiveSession.objects.filter(channel=channel).order_by("-channel__expires_at").first()

            # if no session is found create one
            if not session:
                session = jive.create_session(channel=channel)

            # subscribe to the new lines
            jive.create_session_dialog_subscription(session, *add_lines)

        # record sync event to ensure all connections get a chance to be synced
        connection.last_sync = timezone.now()
        connection.save()

    return HttpResponse(status=202)
