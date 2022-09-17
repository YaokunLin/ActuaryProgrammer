import base64
from contextlib import suppress
import functools
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Set

import dateutil.parser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
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

    # We only care about hangup events because the recording will be ready
    if content["type"] == "announce":
        JiveCallPartial.objects.create(start_time=dateutil.parser.isoparser().isoparse(req["timestamp"]), external_id=content["entityId"])
    elif content["type"] == "replace":
        JiveCallPartial.objects.filter(external_id=content["oldId"]).update(external_id=content["newId"])
    elif content["type"] == "withdraw":
        line: JiveLine = JiveLine.objects.get(external_id=content["subId"], organization_id=content["data"]["originatorOrganizationId"])

        try:
            part = JiveCallPartial.objects.get(external_id=content["entityId"])
        except ObjectDoesNotExist:  # it is possible for duplicate withdraw messages to be sent, so we ignore duplicates
            return HttpResponse(status=202)

        start_time: datetime = part.start_time
        end_time: datetime = dateutil.parser.isoparser().isoparse(req["timestamp"])

        direction: CallDirectionTypes
        if content["data"]["direction"] == "recipient":
            direction = CallDirectionTypes.INBOUND
        else:
            direction = CallDirectionTypes.OUTBOUND

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

        recordings = []
        for recording in content["data"]["recordings"]:
            filename = base64.b64decode(recording["filename"]).decode("utf-8")
            ord = dateutil.parser.isoparser().isoparse(filename.split("~", maxsplit=1)[0].split("/")[-1])

            recordings.append([ord, filename])

        recordings = sorted(recordings, key=lambda r: r[0])

        for recording in recordings:
            ord = recording[0]
            filename = recording[1]

            cp = CallPartial.objects.create(call=call, start_time=ord, end_time=ord)
            cap = CallAudioPartial.objects.create(call_partial=cp, mime_type=SupportedAudioMimeTypes.AUDIO_WAV, status=CallAudioFileStatusTypes.UPLOADED)

            with io.BytesIO() as buf:
                settings.S3_CLIENT.download_fileobj(settings.JIVE_BUCKET_NAME, filename, buf)
                cap.put_file(buf)

            publish_call_audio_partial_saved(call_id=call.id, partial_id=cp.id, audio_partial_id=cap.id)

        part.delete()

    return HttpResponse(status=202)


@api_view(["GET"])
def authentication_connect(request: Request):
    """
    This view returns a redirect to initialize the connect flow with the Jive API.  Users will be redirected to Jive's
    application to confirm access to Peerlogic's systems.

    https://developer.goto.com/guides/Authentication/03_HOW_accessToken/
    """
    return HttpResponseRedirect(redirect_to=generate_jive_callback_url(request))


@api_view(["GET"])
def authentication_connect_url(request: Request):
    """
    This view returns the url to initialize the connect flow with the Jive API.  This is informational to understand what url
    a client must call to present the user Jive's application to confim access to Peerlogic's systems

    https://developer.goto.com/guides/Authentication/03_HOW_accessToken/
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
    authorization_code: str = request.query_params.get("code")
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
        JiveLine.objects.filter(external_id__in=remove_lines).delete()

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
