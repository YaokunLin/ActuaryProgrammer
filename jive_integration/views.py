import base64
import json
import logging
from contextlib import suppress
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

import dateutil.parser
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
    renderer_classes,
)
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from calls.field_choices import CallDirectionTypes
from calls.models import Call
from core.field_choices import VoipProviderIntegrationTypes
from core.models import User
from core.validation import (
    get_practice_telecoms_belonging_to_user,
    get_validated_practice_telecom,
)
from jive_integration.field_choices import JiveEventTypeChoices
from jive_integration.jive_client.client import JiveClient
from jive_integration.models import (
    JiveAWSRecordingBucket,
    JiveChannel,
    JiveConnection,
    JiveLine,
    JiveSession,
)
from jive_integration.serializers import (
    JiveAWSRecordingBucketSerializer,
    JiveConnectionSerializer,
    JiveSubscriptionEventExtractSerializer,
)
from jive_integration.utils import (
    create_peerlogic_call,
    get_call_id_from_previous_announce_events_by_originator_id,
    handle_withdraw_event,
    refresh_connection,
    parse_webhook_from_header,
    get_channel_from_source_jive_id,
)

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

    log.info(f"Jive webhook: Headers: '{request.headers}' POST body '{request.body}'")

    response = HttpResponse(status=202)
    #
    # VALIDATION
    #
    webhook = parse_webhook_from_header(request.headers.get("signature-input"))
    jive_channel = get_channel_from_source_jive_id(webhook)
    if not jive_channel or not jive_channel.active:
        # TODO: 404 was immediately expiring the webhook. this is actually not recoverable right now if we have no other
        # channel activated - we'll shoot ourselves in the foot until we understand this
        log.error(
            f"Jive: Active JiveChannel record does not exist for webhook='{webhook}' - Doing nothing. See https://peerlogictech.atlassian.net/wiki/spaces/PL/pages/471891982/Misconfiguration+Troubleshooting+-+Manual+Backend+Steps#Delete%2FExpire-a-Webhook for more info on how to make sure this expired properly."
        )
        return Response(status=status.HTTP_200_OK, data={"signature": "invalid"})

    try:
        req = json.loads(request.body)
        timestamp_of_request: datetime = dateutil.parser.isoparser().isoparse(req["timestamp"])
        content = json.loads(req["content"])
    except (json.JSONDecodeError, KeyError):
        return HttpResponse(status=status.HTTP_406_NOT_ACCEPTABLE)

    end_time = timestamp_of_request
    jive_request_data_key_value_pair: Dict = content.get("data", {})
    jive_originator_id = jive_request_data_key_value_pair.get("originatorId")
    subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=content)
    subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()
    subscription_event_data = subscription_event_serializer.validated_data

    if not subscription_event_serializer_is_valid:
        log.exception(
            f"Jive: Error from subscription_event_serializer validation from jive_originator_id {jive_originator_id}: {subscription_event_serializer.errors}"
        )
        response = Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": subscription_event_serializer.errors})

    call_direction: CallDirectionTypes
    if jive_request_data_key_value_pair.get("direction") == "recipient":
        call_direction = CallDirectionTypes.INBOUND

    else:
        call_direction = CallDirectionTypes.OUTBOUND

    dialed_number = jive_request_data_key_value_pair.get("ani", "")
    if dialed_number:
        # Example ani's:
        # "ani":"Main Line <+14403883505>"
        # "ani":"+14403883505 <+14403883505>"
        dialed_number = dialed_number.split(" <")[1]
        dialed_number = dialed_number.split(">")[0]

    source_jive_id = content.get("subId")
    source_organization_jive_id = jive_request_data_key_value_pair.get("originatorOrganizationId")
    log.info(f"Jive: Checking we have a JiveLine with originatorOrganizationId='{source_organization_jive_id}'")
    line: JiveLine = JiveLine.objects.filter(source_organization_jive_id=source_organization_jive_id).first()
    log.info(f"Jive: JiveLine found with originatorOrganizationId='{source_organization_jive_id}'")

    channel = line.session.channel
    subscription_event_data.update({"jive_channel_id": channel.id})

    voip_provider_id = line.session.channel.connection.practice_telecom.voip_provider_id
    practice = line.session.channel.connection.practice_telecom.practice

    # Bucket can be overridden for our testing jive account
    bucket_name = line.session.channel.connection.bucket.bucket_name
    if settings.TEST_JIVE_PRACTICE_ID == practice.id:
        bucket_name = settings.JIVE_BUCKET_NAME

    jive_event_type = content.get("type")
    if jive_event_type == JiveEventTypeChoices.ANNOUNCE:
        log.info("Jive: Received jive announce event.")
        peerlogic_call = None

        call_id = get_call_id_from_previous_announce_events_by_originator_id(jive_originator_id)
        if call_id:
            peerlogic_call = Call.objects.get(pk=call_id)

        if not peerlogic_call:
            log.info("Jive: No previous peerlogic call found from previous events in the database - Creating peerlogic call.")
            try:
                peerlogic_call = create_peerlogic_call(
                    jive_request_data_key_value_pair=jive_request_data_key_value_pair,
                    call_direction=call_direction,
                    start_time=timestamp_of_request,
                    dialed_number=dialed_number,
                    practice=practice,
                )
                log.info(f"Jive: Created Peerlogic Call object with id='{peerlogic_call.id}'.")
            except ValidationError:
                log.exception("Error creating a new Peerlogic call.")

        subscription_event_data.update({"peerlogic_call_id": peerlogic_call.id})
        subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=subscription_event_data)
        subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()

    elif jive_event_type == JiveEventTypeChoices.REPLACE:
        log.info("Jive: Received jive replace event.")
        call_id = get_call_id_from_previous_announce_events_by_originator_id(jive_originator_id)
        subscription_event_data.update({"peerlogic_call_id": call_id})
        subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=subscription_event_data)
        subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()

    elif jive_event_type == JiveEventTypeChoices.WITHDRAW:
        log.info("Jive: Received jive withdraw event.")
        try:
            subscription_event_serializer = handle_withdraw_event(
                jive_originator_id=jive_originator_id,
                source_jive_id=source_jive_id,
                voip_provider_id=voip_provider_id,
                end_time=timestamp_of_request,
                subscription_event_data=subscription_event_data,
                jive_request_data_key_value_pair=jive_request_data_key_value_pair,
                bucket_name=bucket_name,
            )
        except Exception:
            log.exception("Jive: Exception during withdraw event.")

    subscription_event_serializer.save()

    return response


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


# TODO: fix, there is something up with the initial content negotiation here. 500s the first time, redirects properly after that.
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
    log.info("Jive: Checking for authorization code in query parameters.")
    authorization_code: Optional[str] = request.query_params.get("code")
    if not authorization_code:
        raise ValidationError({"errors": {"code": "Contact support@peerlogic.com - authorization code is missing from the callback."}})
    log.info("Jive: Found authorization code.")

    log.info("Jive: Instantiating JiveClient.")
    jive: JiveClient = JiveClient(client_id=settings.JIVE_CLIENT_ID, client_secret=settings.JIVE_CLIENT_SECRET)
    log.info("Jive: Instantiated JiveClient.")

    log.info("Jive: Exchanging authorization code for an access token.")
    jive.exchange_code(authorization_code, generate_redirect_uri(request))
    log.info("Jive: Exchanged authorization code for an access token.")

    log.info(f"Jive: Checking for principal (email associated with the user).")
    principal = jive.principal  # this is the email associated with user
    scope = jive.scope  # this is the scope of the authenticated user
    if not principal:
        log.exception("Jive: No principal (email associated with the user) found in access token response.")
        raise ValidationError({"errors": {"principal": "email is missing from your submission - are you logged in?"}})

    log.info("Jive: Refresh token to get account key and organization key.")
    jive.get_token()
    log.info("Jive: Done refreshing token")

    log.info(f"Jive: Checking for existing JiveConnection with principal={principal}.")
    connection: JiveConnection = None
    with suppress(JiveConnection.DoesNotExist):
        connection = JiveConnection.objects.get(practice_telecom__practice__agent__user__email=principal)
        if connection:
            log.info(f"Jive: Found existing JiveConnection with principal={principal}.")

    if not connection:
        log.info(f"Jive: No existing JiveConnection exists with user email principal={principal}.")
        log.info(f"Jive: Validating a Practice Telecom exists with voip_provider__integration_type of JIVE and principal='{principal}'.")
        # TODO: deal with users with multiple practices (Organizations ACL)
        practice_telecom, errors = get_validated_practice_telecom(voip_provider__integration_type=VoipProviderIntegrationTypes.JIVE, email=principal)
        if not practice_telecom:
            log.exception(f"No practice telecom has set up for this Jive customer with user email or principal='{principal}', errors='{errors}'")
            raise ValidationError({"errors": {"code": "Contact support@peerlogic.com - your practice telecom has not been set up with this user yet."}})
        log.info(f"Jive: Successfully validated a Practice Telecom exists with voip_provider__integration_type of JIVE and principal='{principal}'.")

        log.info(
            f"Jive: Creating Jive Connection with practice_telecom='{practice_telecom}', account_key='{jive.account_key}', email='{principal}', organizer_key='{jive.organizer_key}' and scope='{scope}'."
        )
        connection = JiveConnection(practice_telecom=practice_telecom, email=principal)

    connection.refresh_token = jive.refresh_token
    connection.account_key = jive.account_key
    connection.organizer_key = jive.organizer_key
    connection.email = principal
    connection.scope = scope
    log.info(f"Jive: Saving JiveConnection with refresh_token='{jive.refresh_token}.")
    connection.save()
    log.info(f"Jive: Saved JiveConnection to the database with id='{connection.id}'.")

    refresh_connection(connection=connection, request=request)

    query_string_to_append_to_redirect_url = {"connection_id": connection.id}
    # TODO: redirect them back to the application - need to know what route though
    # return redirect(urlencode(query_string_to_append_to_redirect_url))
    return HttpResponse(status=204)


class JiveConnectionViewSet(viewsets.ModelViewSet):
    queryset = JiveConnection.objects.all().order_by("-modified_at")
    serializer_class = JiveConnectionSerializer
    filter_fields = ["practice_telecom", "active"]
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["patch"])
    def refresh(self, request, pk=None):
        if not (self.request.user.is_staff or self.request.user.is_superuser) and not does_practice_of_user_own_connection(connection_id=pk, user=request.user):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Getting JiveConnection from database with pk='{pk}'")
        connection = JiveConnection.objects.get(pk=pk)
        log.info(f"Got JiveConnection from database with pk='{pk}'")

        log.info(f"Refreshing connection for JiveConnection with pk='{pk}'")
        response_data = refresh_connection(connection=connection, request=request)
        log.info(f"Refreshed connection for JiveConnection with pk='{pk}'")

        return Response(status=status.HTTP_200_OK, data=response_data)


def does_practice_of_user_own_connection(connection_id: str, user: User) -> bool:
    connection = JiveConnection.objects.get(pk=connection_id)
    return get_practice_telecoms_belonging_to_user(user).filter(id=connection.practice_telecom.id).exists()


class JiveAWSRecordingBucketViewSet(viewsets.ViewSet):
    queryset = JiveConnection.objects.all().order_by("-modified_at")
    serializer_class = JiveConnectionSerializer

    def get_queryset(self):
        buckets_qs = JiveAWSRecordingBucket.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            buckets_qs = JiveAWSRecordingBucket.objects.all()
        elif self.request.method in SAFE_METHODS:
            # Can see any practice's buckets if you are an assigned agent to a practice
            practice_telecom_ids = get_practice_telecoms_belonging_to_user(user=self.request.user)
            buckets_qs = JiveAWSRecordingBucket.objects.filter(connection__practice_telecom__id__in=practice_telecom_ids)
        return buckets_qs.filter(connection_id=self.kwargs.get("connection_pk")).order_by("-modified_at")

    def list(self, request, connection_pk=None):
        queryset = self.get_queryset().filter(connection_id=connection_pk)
        serializer = JiveAWSRecordingBucketSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, connection_pk=None, pk=None):
        queryset = self.get_queryset().filter(connection_id=connection_pk)
        connection = get_object_or_404(queryset, pk=pk)
        serializer = JiveAWSRecordingBucketSerializer(connection)
        return Response(serializer.data)

    def create(self, request, connection_pk=None):
        if not (self.request.user.is_staff or self.request.user.is_superuser) and not does_practice_of_user_own_connection(
            connection_id=connection_pk, user=request.user
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Jive: Creating JiveAWSRecordingBucket for connection='{connection_pk}")
        bucket = JiveAWSRecordingBucket.objects.create(connection_id=connection_pk)
        bucket.create_bucket()
        log.info(f"Jive: Created JiveAWSRecordingBucket with id='{bucket.id}' connection='{connection_pk}")

        serializer = JiveAWSRecordingBucketSerializer(bucket)
        return Response(status=status.HTTP_201_CREATED, data=serializer.data)

    @action(detail=True, methods=["post"])
    def bucket_credentials(self, request, connection_pk=None, pk=None):
        if not (self.request.user.is_staff or self.request.user.is_superuser) and not does_practice_of_user_own_connection(
            connection_id=connection_pk, user=request.user
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Getting JiveAWSRecordingBucket from database with pk='{pk}'")
        bucket = JiveAWSRecordingBucket.objects.get(pk=pk)
        log.info(f"Got JiveAWSRecordingBucket from database with pk='{pk}'")

        log.info(f"Creating credentials for JiveAWSRecordingBucket with pk='{pk}'")
        response_data = bucket.generate_credentials()
        log.info(f"Created credentials for JiveAWSRecordingBucket with pk='{pk}'")

        return Response(status=status.HTTP_201_CREATED, data=response_data)


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

    # cleanup any expired channels, this will cascade to sessions and lines
    JiveChannel.objects.filter(expires_at__lt=timezone.now()).delete()

    # for each user connection
    for connection in JiveConnection.objects.filter(active=True).order_by("-last_sync"):
        log.info(f"Jive: found connection: {connection}")
        refresh_connection(connection=connection, request=request)

    return HttpResponse(status=202)
