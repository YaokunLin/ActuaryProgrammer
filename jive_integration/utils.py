import base64
import logging
from datetime import datetime, timedelta
from time import sleep
from typing import Dict, List, Optional, Set, Tuple

import dateutil
import shortuuid
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.serializers import ValidationError

from calls.field_choices import CallConnectionTypes, CallDirectionTypes
from calls.models import Call, CallPartial
from calls.serializers import CallSerializer, CallWriteSerializer
from core.models import Practice
from core.validation import is_extension
from jive_integration.exceptions import RefreshTokenNoLongerRefreshableException
from jive_integration.jive_client.client import JiveClient, Line
from jive_integration.models import (
    JiveChannel,
    JiveAPICredentials,
    JiveLine,
    JiveSession,
    JiveSubscriptionEventExtract,
)
from jive_integration.publishers import publish_leg_b_ready_event
from jive_integration.serializers import JiveSubscriptionEventExtractSerializer

US_TELEPHONE_NUMBER_DIGIT_LENGTH = 10
# Get an instance of a logger
log = logging.getLogger(__name__)


def create_peerlogic_call(call_id: str, jive_request_data_key_value_pair: Dict, start_time: datetime, dialed_number: str, practice: Practice) -> Call:
    log.info(f"Jive: Creating Peerlogic Call object with start_time='{start_time}'.")

    call_direction: CallDirectionTypes
    if jive_request_data_key_value_pair.get("direction") == "recipient":
        call_direction = CallDirectionTypes.INBOUND
        # inbound for now - will check if both callee and caller are extensions instead of Telephone Numbers
        # to detect internal
    else:
        call_direction = CallDirectionTypes.OUTBOUND

    jive_callee_number = jive_request_data_key_value_pair.get("callee", {}).get("number")
    jive_callee_number_is_extension = is_extension(jive_callee_number)
    jive_caller_number = jive_request_data_key_value_pair.get("caller", {}).get("number")
    jive_caller_number_is_extension = is_extension(jive_caller_number)
    sip_callee_extension = ""
    sip_callee_number = ""
    sip_caller_extension = ""
    sip_caller_number = ""

    # both extensions?
    if jive_callee_number_is_extension and jive_caller_number_is_extension:
        sip_callee_extension = jive_callee_number
        sip_caller_extension = jive_caller_number
        call_direction = CallDirectionTypes.INTERNAL
    else:
        # if just callee is an extension (between 3-6 digits):
        if jive_callee_number_is_extension:
            sip_callee_extension = jive_callee_number
            sip_callee_number = dialed_number
            sip_caller_number = f"+1{jive_caller_number}"
        # if caller is an extension (between 3-6 digits):
        if jive_caller_number_is_extension:
            sip_caller_extension = jive_caller_number
            sip_caller_number = dialed_number
            sip_callee_number = f"+1{jive_callee_number}"
        if not sip_callee_number:
            sip_callee_number = jive_callee_number
        # TODO: Logic for outbound caller number for practice - no ani present

    call_fields = {
        "id": call_id,
        "practice": practice,
        "call_start_time": start_time,
        "duration_seconds": timedelta(seconds=0),
        # TODO: connect_duration_seconds logic
        # TODO: progress_time_seconds logic
        # TODO: hold_time_seconds logic
        "call_direction": call_direction,
        "sip_callee_extension": sip_callee_extension,
        "sip_callee_number": sip_callee_number,
        "sip_callee_name": jive_request_data_key_value_pair.get("callee", {}).get("name"),
        "sip_caller_extension": sip_caller_extension,
        "sip_caller_number": sip_caller_number,
        "sip_caller_name": jive_request_data_key_value_pair.get("caller", {}).get("name"),
        "checked_voicemail": False,  # TODO: determine value in downstream subscribing cloud functions
        "went_to_voicemail": False,  # TODO: determine value in downstream subscribing cloud functions
    }

    log.info(f"Jive: Call fields determined: call_fields='{call_fields}'")

    peerlogic_call_serializer = CallWriteSerializer(data=call_fields)
    peerlogic_call_serializer_is_valid = peerlogic_call_serializer.is_valid()
    peerlogic_call_serializer_errors: Dict = dict(peerlogic_call_serializer.errors)

    # TODO: practice field keeps giving the practice name instead of the pk...
    # not sure how to remedy, but it keeps saving the call correctly despite this validation error.
    # popping for now.
    peerlogic_call_serializer_errors.pop("practice")
    if not peerlogic_call_serializer_is_valid and peerlogic_call_serializer_errors:
        log.exception(f"Jive: Error from peerlogic_call_serializer validation: {peerlogic_call_serializer_errors}")
        raise ValidationError(peerlogic_call_serializer_errors)

    return Call.objects.create(**call_fields)


def get_or_create_call_id(originator_id: str) -> Tuple[bool, str]:
    call_id = get_call_id_from_previous_announce_events_by_originator_id(originator_id)
    if call_id:
        log.info(f"Jive: Returning call_id from an existing announce event extract only - call_id='{call_id}'")
        exists_in_db = True
        return exists_in_db, call_id

    # Proceed to check the cache
    CACHE_TIMEOUT = 600  # 10 minutes
    cache_key = f"jive.originator_id.{originator_id}"
    call_id = shortuuid.uuid()
    log.info(f"Jive: Getting call_id for cache_key='{cache_key}'")
    was_created = cache.set(cache_key, call_id, nx=True, timeout=CACHE_TIMEOUT)
    if not was_created:
        call_id = cache.get(cache_key)
        # check events for announce
        log.info(f"Jive: Returning existing call_id='{call_id}' for cache_key='{cache_key}'")
        exists_in_db = True
        return exists_in_db, call_id

    log.info(f"Jive: Returning new call_id='{call_id}' for cache_key='{cache_key}'")
    exists_in_db = False
    return exists_in_db, call_id


def get_call_id_from_previous_announce_event(entity_id: str) -> str:
    log.info(f"Jive: Checking if there is a prdsevious announce subscription event with this entity_id='{entity_id}'.")
    try:
        return JiveSubscriptionEventExtract.objects.get(jive_type="announce", entity_id=entity_id).peerlogic_call_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"Jive: No JiveSubscriptionEventExtract found with type='announce' and given entity_id='{entity_id}'")


def get_subscription_event_from_previous_announce_event(leg_id: str) -> JiveSubscriptionEventExtract:
    log.info(f"Jive: Checking if there is a previous announce subscription event with this leg_id='{leg_id}'.")
    try:
        return JiveSubscriptionEventExtract.objects.get(jive_type="announce", data_leg_id=leg_id)
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"Jive: No JiveSubscriptionEventExtract found with type='announce' and given leg_id='{leg_id}'")


def get_call_id_from_previous_announce_events_by_originator_id(originator_id: str) -> str:
    log.info(f"Jive: Checking if there is a previous announce subscription event with this originator_id='{originator_id}'.")
    try:
        event = JiveSubscriptionEventExtract.objects.filter(jive_type="announce", data_originator_id=originator_id).first()
        if event:
            return event.peerlogic_call_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"Jive: No JiveSubscriptionEventExtract found with type='announce' and given originator_id='{originator_id}'")
        return ""  # Blankable call id


def get_channel_from_source_jive_id(webhook: str) -> JiveChannel:
    log.info(f"Jive: Finding channel record with matching source_jive_id: '{webhook}'")
    try:
        return JiveChannel.objects.get(source_jive_id=webhook)
    except JiveChannel.DoesNotExist:
        log.info(f"Jive: No JiveChannel found with source_jive_id: '{webhook}'")


def get_call_partial_id_from_previous_withdraw_event_by_originator_id(originator_id: str, data_recordings_extract: List[Dict[str, str]]) -> Optional[str]:
    log.info(f"Jive: Checking if there is a previous withdraw subscription event with this originator_id='{originator_id} and recording list.")
    try:
        event = (
            JiveSubscriptionEventExtract.objects.filter(jive_type="withdraw", data_originator_id=originator_id, data_recordings_extract=data_recordings_extract)
            .order_by("-data_created")
            .first()
        )
        if event:
            return event.peerlogic_call_partial_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"Jive: No JiveSubscriptionEventExtract found with type='withdrawal' and given originator_id='{originator_id}' with the same recording list.")
        return ""


def wait_for_peerlogic_call(call_id: str, current_attempt: int = 1) -> str:
    """Will sleep for 1 second for each attempt"""
    MAX_ATTEMPTS = 3

    try:
        log.info(f"Trying to get a call from call_id='{call_id}'")
        call = Call.objects.get(pk=call_id)
        log.info(f"Successfully got a call from call_id='{call_id}'")
        return call
    except Call.DoesNotExist:
        if current_attempt >= MAX_ATTEMPTS:
            raise
        sleep(1)
        return wait_for_peerlogic_call(call_id=call_id, current_attempt=current_attempt + 1)


def handle_withdraw_event(
    jive_originator_id: str,
    source_jive_id: str,
    voip_provider_id: str,
    end_time: datetime,
    event: JiveSubscriptionEventExtract,
    jive_request_data_key_value_pair: Dict,
    bucket_name: str,
) -> Tuple[JiveSubscriptionEventExtract, str]:
    call_id = get_call_id_from_previous_announce_events_by_originator_id(jive_originator_id)
    log.info(f"Jive: Call ID is {call_id}")
    event.peerlogic_call_id = call_id
    event.save()

    jive_request_recordings = jive_request_data_key_value_pair.get("recordings", [])
    recording_count = len(jive_request_recordings)
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
    else:  # recording_count > 0:
        initial_withdraw_id = get_call_partial_id_from_previous_withdraw_event_by_originator_id(
            originator_id=jive_originator_id, data_recordings_extract=jive_request_recordings
        )
        if initial_withdraw_id:
            log.info(f"Jive: Recording found and call partial already created from a separate line earlier: '{initial_withdraw_id}' - skipping publishing.")
            return event, call_id

    recordings = []
    for recording in jive_request_recordings:
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

        jive_leg_created_time = event.data_created

        cp = CallPartial.objects.create(call=peerlogic_call, time_interaction_started=jive_leg_created_time, time_interaction_ended=end_time)
        log.info(
            f"Jive: Created Peerlogic CallPartial with cp.id='{cp.id}', peerlogic_call.id='{peerlogic_call.id}', time_interaction_started='{peerlogic_call.call_start_time}' and time_interaction_ended='{end_time}'."
        )

        event.peerlogic_call_partial_id = cp.id
        event.save()

        publish_leg_b_ready_event(
            jive_call_subscription_id=source_jive_id,
            voip_provider_id=voip_provider_id,
            event={
                "jive_originator_id": jive_originator_id,
                "peerlogic_call_id": peerlogic_call.id,
                "peerlogic_call_partial_id": cp.id,
                "filename": filename_encoded,
                "bucket_name": bucket_name,
            },
        )

    return event, call_id


def resync_connection(connection: JiveAPICredentials, request: Request):
    # to avoid timeouts we want to complete execution in 30s
    deadline = datetime.now() + timedelta(seconds=60)
    jive: JiveClient = JiveClient(
        client_id=settings.JIVE_CLIENT_ID,
        client_secret=settings.JIVE_CLIENT_SECRET,
        access_token=connection.access_token,
        refresh_token=connection.refresh_token,
    )
    if deadline < datetime.now():
        raise RefreshTokenNoLongerRefreshableException()

    for channel in JiveChannel.objects.filter(connection=connection, active=True):
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
    external_lines: Set[Line] = set(jive.list_lines_all_users(connection.account_key))

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


def parse_webhook_from_header(header: str) -> str:
    # Example format:
    # 'sig1=("@request-target" "date" "digest");keyid="Webhook.2427ad08-0624-454b-99ce-d05d23f08d0e";alg="hmac-sha256";created=1668543156;expires=1668543456;nonce="/Hny/Qbs+5o="'
    # We need to grab the keyid value
    return header.split('keyid="')[1].split('";alg=')[0]
