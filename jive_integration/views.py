import json
import logging
from contextlib import suppress
from datetime import datetime
from typing import Dict, Optional

import dateutil.parser
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
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

from core.field_choices import VoipProviderIntegrationTypes
from core.models import User
from core.validation import (
    get_practice_telecoms_belonging_to_user,
    get_validated_practice_telecom,
)
from jive_integration.exceptions import RefreshTokenNoLongerRefreshableException
from jive_integration.field_choices import JiveEventTypeChoices
from jive_integration.jive_client.client import JiveClient
from jive_integration.models import (
    JiveAPICredentials,
    JiveAWSRecordingBucket,
    JiveChannel,
    JiveLine,
)
from jive_integration.serializers import (
    JiveAPICredentialsSerializer,
    JiveAWSRecordingBucketSerializer,
    JiveChannelSerializer,
    JiveSubscriptionEventExtractSerializer,
)
from jive_integration.utils import (
    create_peerlogic_call,
    get_call_id_from_previous_announce_events_by_originator_id,
    get_channel_from_source_jive_id,
    get_or_create_call_id,
    handle_withdraw_event,
    parse_webhook_from_header,
    resync_from_credentials,
    wait_for_peerlogic_call,
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

    # Documentation on webhook: https://developer.goto.com/GoToConnect/#section/Webhook
    #
    # BE CAREFUL WITH THE RESPONSE STATUS CODES returned from this endpoint. Certain statuses will disable the webhook for the GoTo account!
    #
    # Webhook URL Becoming Invalid
    # - If the server returns a 410 Gone or a 404 Not Found on a request, the webhook channel will be automatically deleted.
    # Webhook Request Failure
    # - In the case where the response received is a server error (5XX), the webhook request will follow the retry policy.
    # Webhook Request Timeout
    # - A Webhook notification is considered incomplete or timed out if a response is not provided in 4,000 ms or less.
    # - The webhook notification request will follow the retry policy.
    # Webhook Request Retry Policy
    # - In the event that a webhook request failed, the webhook request will be retried up to 2 more times in quick succession before it is abandoned.

    log_prefix = "Jive: Webhook received event."
    log.info(f"{log_prefix} headers='{request.headers}' body='{request.body}'")

    response = HttpResponse(status=202)
    #
    # VALIDATION
    #
    webhook = parse_webhook_from_header(request.headers.get("signature-input"))
    log_prefix = f"{log_prefix}. webhook='{webhook}'"
    jive_channel = get_channel_from_source_jive_id(webhook)
    if not jive_channel or not jive_channel.active:
        log.error(
            f"{log_prefix} Active JiveChannel record does not exist for webhook! - Sending response to invalidate the webhook. jive_channel='{jive_channel}'. If this is a practice that should stay connected, you must run resync for them immediately in order to recreate the channel and to not miss call data!"
        )
        return Response(status=status.HTTP_404_NOT_FOUND, data={"signature": "invalid"})

    try:
        req = json.loads(request.body)
        timestamp_of_request: datetime = dateutil.parser.isoparser().isoparse(req["timestamp"])
        content = json.loads(req["content"])
    except (json.JSONDecodeError, KeyError):
        log.error(f"{log_prefix} Could not determine timestamp of request. Invalid response sent to webhook.")
        return HttpResponse(status=status.HTTP_406_NOT_ACCEPTABLE)

    log.info(f"{log_prefix} Validating event")
    end_time = timestamp_of_request
    jive_request_data_key_value_pair: Dict = content.get("data", {})
    jive_originator_id = jive_request_data_key_value_pair.get("originatorId")
    subscription_event_serializer = JiveSubscriptionEventExtractSerializer(data=content)
    subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()
    subscription_event_data = subscription_event_serializer.validated_data

    if not subscription_event_serializer_is_valid:
        log.error(
            f"{log_prefix} Error from subscription_event_serializer validation from jive_originator_id='{jive_originator_id}': errors='{subscription_event_serializer.errors}'. Setting response to invalid. Further processing will resume but may throw errors."
        )
        response = Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": subscription_event_serializer.errors})

    log.info(f"{log_prefix} Validated event.")
    event = subscription_event_serializer.save()
    log.prefix = f"{log_prefix} event='{event.id}'"
    log.info(f"{log_prefix} Event saved. event='{event}'")

    dialed_number = jive_request_data_key_value_pair.get("ani", "")
    if dialed_number:
        # Example ani's:
        # "ani":"Main Line <+14403883505>"
        # "ani":"+14403883505 <+14403883505>"
        dialed_number = dialed_number.split(" <")[1]
        dialed_number = dialed_number.split(">")[0]

    source_jive_id = content.get("subId")
    source_organization_jive_id = jive_request_data_key_value_pair.get("originatorOrganizationId")
    log.info(f"{log_prefix} Checking we have a JiveLine with originatorOrganizationId='{source_organization_jive_id}'")
    line: JiveLine = JiveLine.objects.filter(source_organization_jive_id=source_organization_jive_id).first()
    log.info(f"{log_prefix} JiveLine found with originatorOrganizationId='{source_organization_jive_id}'")

    channel = line.session.channel
    subscription_event_data.update({"jive_channel_id": channel.id})

    voip_provider_id = line.session.channel.jive_api_credentials.practice_telecom.voip_provider_id
    practice = line.session.channel.jive_api_credentials.practice_telecom.practice

    # Bucket can be overridden for our testing jive account
    bucket_name = line.session.channel.jive_api_credentials.bucket.bucket_name
    if settings.TEST_JIVE_PRACTICE_ID == practice.id:
        bucket_name = settings.JIVE_BUCKET_NAME

    call_id = ""
    jive_event_type = content.get("type")
    if jive_event_type == JiveEventTypeChoices.ANNOUNCE:
        log.info(f"{log_prefix} Received jive announce event")

        call_exists, call_id = get_or_create_call_id(jive_originator_id)
        if call_exists:
            peerlogic_call = wait_for_peerlogic_call(call_id=call_id)
        else:
            log.info(f"{log_prefix} No previous peerlogic call found from previous events in the database - Creating peerlogic call.")
            try:
                peerlogic_call = create_peerlogic_call(
                    call_id=call_id,
                    jive_request_data_key_value_pair=jive_request_data_key_value_pair,
                    start_time=timestamp_of_request,
                    dialed_number=dialed_number,
                    practice=practice,
                )
                call_id = peerlogic_call.id
                log.info(f"Jive: Created Peerlogic Call object with id='{peerlogic_call.id}'.")
            except ValidationError:
                log.exception(f"Error creating a new Peerlogic call.")

    elif jive_event_type == JiveEventTypeChoices.REPLACE:
        log.info(f"{log_prefix} Received jive replace event.")
        call_id = get_call_id_from_previous_announce_events_by_originator_id(jive_originator_id)

    elif jive_event_type == JiveEventTypeChoices.WITHDRAW:
        log.info(f"{log_prefix} Received jive withdraw event.")
        try:
            event, call_id = handle_withdraw_event(
                jive_originator_id=jive_originator_id,
                source_jive_id=source_jive_id,
                voip_provider_id=voip_provider_id,
                end_time=end_time,
                event=event,
                jive_request_data_key_value_pair=jive_request_data_key_value_pair,
                bucket_name=bucket_name,
            )
            log.info(f"{log_prefix} Handled jive withdraw event.")
        except Exception as e:
            log.exception(f"{log_prefix} Exception='{e}' occurred during withdraw event.")
            return response  # must return here since we may not have a valid call_id

    # always get the call_id onto the event
    event.peerlogic_call_id = call_id
    event.save()

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
    Refresh tokens are stored on `JiveAPICredentials` objects and linked to a practice.  If a jive_api_credentials object is not
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
    try:
        jive.refresh_for_new_token()
    except RefreshTokenNoLongerRefreshableException as e:
        raise ValidationError({"errors": {"refresh_token": "Your GoTo account is no longer able to connect to Peerlogic - contact support@peerlogic.com."}})
    log.info("Jive: Done refreshing token.")

    log.info(f"Jive: Checking for existing JiveAPICredentials with principal={principal}.")
    jive_api_credentials: JiveAPICredentials = None
    with suppress(JiveAPICredentials.DoesNotExist):
        jive_api_credentials = JiveAPICredentials.objects.get(practice_telecom__practice__agent__user__email=principal)
        if jive_api_credentials:
            log.info(f"Jive: Found existing JiveAPICredentials with principal={principal}.")

    if not jive_api_credentials:
        log.info(f"Jive: No existing JiveAPICredentials exists with user email principal={principal}.")
        log.info(f"Jive: Validating a Practice Telecom exists with voip_provider__integration_type of JIVE and principal='{principal}'.")
        # TODO: deal with users with multiple practices (Organizations ACL)
        practice_telecom, errors = get_validated_practice_telecom(voip_provider__integration_type=VoipProviderIntegrationTypes.JIVE, email=principal)
        if not practice_telecom:
            log.exception(f"No practice telecom has set up for this Jive customer with user email or principal='{principal}', errors='{errors}'")
            raise ValidationError({"errors": {"code": "Contact support@peerlogic.com - your practice telecom has not been set up with this user yet."}})
        log.info(f"Jive: Successfully validated a Practice Telecom exists with voip_provider__integration_type of JIVE and principal='{principal}'.")

        log.info(
            f"Jive: Creating JiveAPICredentials with practice_telecom='{practice_telecom}', account_key='{jive.account_key}', email='{principal}', organizer_key='{jive.organizer_key}' and scope='{scope}'."
        )
        jive_api_credentials = JiveAPICredentials(practice_telecom=practice_telecom, email=principal)

    jive_api_credentials.access_token = jive.access_token
    jive_api_credentials.refresh_token = jive.refresh_token
    jive_api_credentials.account_key = jive.account_key
    jive_api_credentials.organizer_key = jive.organizer_key
    jive_api_credentials.email = principal
    jive_api_credentials.scope = scope
    log.info(f"Jive: Saving JiveAPICredentials with access_token='{jive.access_token}.")
    jive_api_credentials.save()
    log.info(f"Jive: Saved JiveAPICredentials to the database with id='{jive_api_credentials.id}'.")

    resync_from_credentials(jive_api_credentials=jive_api_credentials, request=request)

    query_string_to_append_to_redirect_url = {"jive_api_credentials_id": jive_api_credentials.id}
    # TODO: redirect them back to the application - need to know what route though
    # return redirect(urlencode(query_string_to_append_to_redirect_url))
    return HttpResponse(status=204)


class JiveChannelViewSet(viewsets.ModelViewSet):
    queryset = JiveChannel.objects.all().order_by("-modified_at")
    filter_fields = ["active", "source_jive_id"]
    serializer_class = JiveChannelSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return super().get_queryset().filter(jive_api_credentials=self.kwargs.get("jive_api_credentials_pk"))

    def destroy(self, request, pk=None, jive_api_credentials_pk=None):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Jive: Getting JiveChannel from database with pk='{pk}'")
        channel = get_object_or_404(self.get_queryset(), pk=pk)
        log.info(f"Jive: Got JiveChannel from database with pk='{pk}'")

        jive_api_credentials = channel.jive_api_credentials

        log.info(f"Jive: Instantiating JiveClient with jive_api_credentials.id='{jive_api_credentials.id}'")
        jive: JiveClient = JiveClient(client_id=settings.JIVE_CLIENT_ID, client_secret=settings.JIVE_CLIENT_SECRET, jive_api_credentials=jive_api_credentials)
        log.info("Jive: Instantiated JiveClient with jive_api_credentials.id='{jive_api_credentials.id}'")

        log.info(f"Jive: Deleting webhook channel jive-side and deactivating peerlogic-side for JiveChannel with pk='{pk}'")
        successfully_deleted_jive_side = False  # this is not needed in the current code but is kept here in case someone modifies the code-path below
        try:
            channel = jive.delete_webhook_channel(channel=channel)
            successfully_deleted_jive_side = True
            log.info(
                f"Jive: Successfully deleted webhook channel jive-side and deactivated peerlogic-side for JiveChannel with pk='{channel.pk}', active='{channel.active}'"
            )
        except Exception as e:
            log.exception(f"Jive: Could not delete webhook channel channel={channel}. Encountered exception='{e}' Setting to inactive in the RDBMS.")
            successfully_deleted_jive_side = False
            channel.active = False
            channel.save()
            log.info(f"Jive: Set JiveChannel to inactive with pk='{channel.pk}', active='{channel.active}'")

        jive_channel_serializer = JiveChannelSerializer(channel)
        return Response(
            status=status.HTTP_200_OK, data={"channel": jive_channel_serializer.data, "successfully_deleted_jive_side": successfully_deleted_jive_side}
        )


class JiveAPICredentialsViewSet(viewsets.ModelViewSet):
    queryset = JiveAPICredentials.objects.all().order_by("-modified_at")
    serializer_class = JiveAPICredentialsSerializer
    filter_fields = ["practice_telecom", "active"]
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["patch"])
    def resync(
        self,
        request,
        pk=None,
    ):
        if not (self.request.user.is_staff or self.request.user.is_superuser) and not does_practice_of_user_own_jive_api_credentials(
            jive_api_credentials_id=pk, user=request.user
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Getting JiveAPICredentials from database with pk='{pk}'")
        jive_api_credentials = JiveAPICredentials.objects.get(pk=pk)
        log.info(f"Got JiveAPICredentials from database with pk='{pk}'")

        log.info(f"Resyncing jive_api_credentials for JiveAPICredentials with pk='{pk}'")
        try:
            response_data = resync_from_credentials(jive_api_credentials=jive_api_credentials, request=request)
        except RefreshTokenNoLongerRefreshableException as e:
            error_message = f"Jive: resync endpoint: Found no longer refreshable api credentials for jive_api_credentials.id='{jive_api_credentials.id}."
            log.exception(error_message)
            raise ValidationError({"error": error_message})

        log.info(f"Jive: Resynced jive_api_credentials for JiveAPICredentials with pk='{pk}'")

        return Response(status=status.HTTP_200_OK, data=response_data)


def does_practice_of_user_own_jive_api_credentials(jive_api_credentials_id: str, user: User) -> bool:
    jive_api_credentials = JiveAPICredentials.objects.get(pk=jive_api_credentials_id)
    return get_practice_telecoms_belonging_to_user(user).filter(id=jive_api_credentials.practice_telecom.id).exists()


class JiveAWSRecordingBucketViewSet(viewsets.ModelViewSet):
    queryset = JiveAWSRecordingBucket.objects.all().order_by("-modified_at")
    serializer_class = JiveAWSRecordingBucketSerializer
    filter_fields = ["practice_telecom"]

    def get_queryset(self):
        buckets_qs = JiveAWSRecordingBucket.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            buckets_qs = JiveAWSRecordingBucket.objects.all()
        elif self.request.method in SAFE_METHODS:
            # Can see any practice's buckets if you are an assigned agent to a practice
            practice_telecom_ids = get_practice_telecoms_belonging_to_user(user=self.request.user)
            buckets_qs = JiveAWSRecordingBucket.objects.filter(practice_telecom__id__in=practice_telecom_ids)
        return buckets_qs.order_by("-modified_at")

    def create(self, request: Request, practice_telecom_pk: str = None) -> Response:
        # TODO: test non-admin request
        practice_telecom_pk = self.request.data.get("practice_telecom")
        if not (practice_telecom_pk) and (
            self.request.user.is_staff or self.request.user.is_superuser or practice_telecom_pk in get_practice_telecoms_belonging_to_user(request.user)
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Jive: Creating JiveAWSRecordingBucket for practice_telecom_pk='{practice_telecom_pk}")
        bucket = JiveAWSRecordingBucket.objects.create(practice_telecom_id=practice_telecom_pk)
        bucket.create_bucket()
        log.info(f"Jive: Created JiveAWSRecordingBucket with id='{bucket.id}' practice_telecom_pk='{practice_telecom_pk}")

        serializer = JiveAWSRecordingBucketSerializer(bucket)
        return Response(status=status.HTTP_201_CREATED, data=serializer.data)

    @action(detail=True, methods=["post"])
    def bucket_credentials(self, request: Request, pk: str = None) -> Response:
        # TODO: test non-admin request
        practice_telecom_pk = self.request.data.get("practice_telecom_pk")
        if not (self.request.user.is_staff or self.request.user.is_superuser or practice_telecom_pk in get_practice_telecoms_belonging_to_user(request.user)):
            return Response(status=status.HTTP_404_NOT_FOUND)

        log.info(f"Getting JiveAWSRecordingBucket from database with pk='{pk}'")
        bucket = self.get_queryset().get(pk=pk)
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
    Jive event subscriptions must be resynced every week. Additionally, there is no push event when a line is added
    or removed from an account.   This endpoint will sync the lines from jive for each active jive_api_credentials.
    JiveAPICredentials are prioritized by the longest interval since the last sync.  Any stale or invalid channels will be garbage
    collected though the records may remain in the database for a period to ensure any latent events sent to the
    webhook receiver will still be routed correctly.
    """
    log.info("Jive: syncing jive lines and subscriptions")

    # cleanup any expired channels, this will cascade to sessions and lines
    JiveChannel.objects.filter(expires_at__lt=timezone.now()).delete()

    # for each user jive_api_credentials
    for jive_api_credentials in JiveAPICredentials.objects.filter(active=True).order_by("-last_sync"):
        log.info(f"Jive: found jive_api_credentials: {jive_api_credentials}")
        try:
            resync_from_credentials(jive_api_credentials=jive_api_credentials, request=request)
        except RefreshTokenNoLongerRefreshableException as e:
            log.exception(f"Found not refreshable connection for jive_api_credentials.id='{jive_api_credentials.id}. Continuing.")

    return HttpResponse(status=202)
