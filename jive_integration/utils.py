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
from calls.serializers import CallWriteSerializer
from core.models import Practice
from jive_integration.field_choices import JiveEventTypeChoices, JiveLegStateChoices
from core.validation import is_extension
from jive_integration.exceptions import RefreshTokenNoLongerRefreshableException
from jive_integration.jive_client.client import JiveClient, Line
from jive_integration.models import (
    JiveAPICredentials,
    JiveChannel,
    JiveLine,
    JiveSession,
    JiveSubscriptionEventExtract,
)
from jive_integration.publishers import publish_leg_b_ready_event

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
        log.info(f"Jive: Returning call_id from an existing announce event extract call_id='{call_id}', originator_id='{originator_id}'")
        exists_in_db = True
        return exists_in_db, call_id

    # Proceed to check the cache
    log.info(f"Jive: call_id not found in the RDBMS. Checking cache.")
    CACHE_TIMEOUT = 600  # 10 minutes
    cache_key = f"jive.originator_id.{originator_id}"

    call_id = shortuuid.uuid()
    log.info(f"Jive: Getting call_id for cache_key='{cache_key}'")
    was_created = cache.set(cache_key, call_id, nx=True, timeout=CACHE_TIMEOUT)
    if not was_created:
        # the cache_key and a previously existing call_id were stored, get the stored call_id
        call_id = cache.get(cache_key)
        log.info(f"Jive: Returning existing call_id='{call_id}' for cache_key='{cache_key}'")
        exists_in_db = True
        return exists_in_db, call_id

    log.info(f"Jive: Returning new call_id='{call_id}' for cache_key='{cache_key}'")
    exists_in_db = False
    return exists_in_db, call_id

def calculate_connect_duration(originator_id: str) -> int:
    # Grab first jive ringing state for the call id
    ringing_event = (
        JiveSubscriptionEventExtract.objects.filter(data_state=JiveLegStateChoices.CREATED, data_originator_id=originator_id).order_by("-data_created").first()
    )
    # Grab first jive answer state for the call id
    answered_event = (
        JiveSubscriptionEventExtract.objects.filter(data_state=JiveLegStateChoices.ANSWERED, data_originator_id=originator_id).order_by("-data_created").first()
    )
    # Subtract the time
    if ringing_event and answered_event:
        return answered_event.created_at - ringing_event.created_at
    return None


def calculate_progress_time(originator_id: str, end_time: datetime) -> int:
    # Grab first jive answer state for the call id
    answered_event = (
        JiveSubscriptionEventExtract.objects.filter(data_state=JiveLegStateChoices.ANSWERED, data_originator_id=originator_id).order_by("-data_created").first()
    )

    # Subtract the time
    if end_time and answered_event:
        return end_time - answered_event.created_at
    return None

def get_call_id_from_previous_announce_events_by_originator_id(originator_id: str) -> str:
    log.info(f"Jive: Checking if there is a previous announce subscription event with this originator_id='{originator_id}' in the RDBMS.")
    try:
        event = JiveSubscriptionEventExtract.objects.filter(jive_type=JiveEventTypeChoices.ANNOUNCE, data_originator_id=originator_id).first()
        if event:
            return event.peerlogic_call_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"Jive: No JiveSubscriptionEventExtract found with type='announce' and given originator_id='{originator_id}' in the RDBMS.")
        return ""  # Blankable call id


def get_channel_from_source_jive_id(webhook: str) -> Optional[JiveChannel]:
    log.info(f"Jive: Finding channel record with matching source_jive_id='{webhook}'")
    try:
        return JiveChannel.objects.get(source_jive_id=webhook)
    except JiveChannel.DoesNotExist:
        log.info(f"Jive: No JiveChannel found with source_jive_id='{webhook}'")
        return None


def calculate_connect_duration(originator_id: str) -> int:
    # Grab first jive ringing state for the call id
    ringing_event = (
        JiveSubscriptionEventExtract.objects.filter(data_state=JiveLegStateChoices.CREATED, data_originator_id=originator_id).order_by("-data_created").first()
    )
    # Grab first jive answer state for the call id
    answered_event = (
        JiveSubscriptionEventExtract.objects.filter(data_state=JiveLegStateChoices.ANSWERED, data_originator_id=originator_id).order_by("-data_created").first()
    )
    # Subtract the time
    if ringing_event and answered_event:
        return answered_event.created_at - ringing_event.created_at
    return None


def calculate_progress_time(originator_id: str, end_time: datetime) -> int:
    # Grab first jive answer state for the call id
    answered_event = (
        JiveSubscriptionEventExtract.objects.filter(data_state=JiveLegStateChoices.ANSWERED, data_originator_id=originator_id).order_by("-data_created").first()
    )

    # Subtract the time
    if end_time and answered_event:
        return end_time - answered_event.created_at
    return None


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
    SLEEP_TIME_SECONDS = 1

    try:
        log.info(f"Trying to get a call from call_id='{call_id}'")
        call = Call.objects.get(pk=call_id)
        log.info(f"Successfully got a call from call_id='{call_id}'")
        return call
    except Call.DoesNotExist:
        if current_attempt >= MAX_ATTEMPTS:
            raise
        sleep(SLEEP_TIME_SECONDS)
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

    event_id = event.id
    log_prefix = f"Jive: Handling withdraw event {event_id} -"
    log.info(f"{log_prefix} Finding associated call_id")
    call_id = get_call_id_from_previous_announce_events_by_originator_id(jive_originator_id)
    log.info(f"{log_prefix} Found associated call_id='{call_id}'")

    # handle case where we do not have any preceding events (somehow)
    if not call_id:
        raise Exception(
            f"{log_prefix} Unable to find call_id='{call_id}'! There should already be an associated call_id for an earlier announce event but none was found!"
        )

    log.info(f"{log_prefix} Associating call_id='{call_id}' and saving to RDBMS.")
    event.peerlogic_call_id = call_id
    event.save()
    log.info(f"{log_prefix} Associated call_id='{call_id}' and saved to RDBMS.")

    log_prefix = f"{log_prefix} call_id='{call_id}' -"
    log.info(f"{log_prefix} Extracting recording count from {event_id}")
    jive_request_recordings = jive_request_data_key_value_pair.get("recordings", [])
    recording_count = len(jive_request_recordings)
    log.info(f"{log_prefix} Found {recording_count} recordings.")

    if recording_count == 0:
        # TODO: call Jive API to see if there is a corresponding Voicemail
        log.info(f"{log_prefix} Updating Peerlogic call end time and duration for call_id='{call_id}'")
        peerlogic_call = Call.objects.get(pk=call_id)
        peerlogic_call.call_end_time = end_time
        peerlogic_call.duration_seconds = peerlogic_call.call_end_time - peerlogic_call.call_start_time
        peerlogic_call.progress_time_seconds = calculate_progress_time(originator_id=jive_originator_id, end_time=end_time)
        peerlogic_call.connect_duration_seconds = calculate_connect_duration(originator_id=jive_originator_id)
        peerlogic_call.call_connection = CallConnectionTypes.MISSED
        peerlogic_call.save()
        log.info(
            f"{log_prefix} Updated Peerlogic call with the following fields: peerlogic_call.call_connection='{peerlogic_call.call_connection}', peerlogic_call.call_end_time='{peerlogic_call.call_end_time}', peerlogic_call.duration_seconds='{peerlogic_call.duration_seconds}'"
        )
    else:  # recording_count > 0:
        initial_withdraw_id = get_call_partial_id_from_previous_withdraw_event_by_originator_id(
            originator_id=jive_originator_id, data_recordings_extract=jive_request_recordings
        )
        if initial_withdraw_id:
            log.info(
                f"{log_prefix} Recording found and call partial already created from a separate line earlier: '{initial_withdraw_id}' - skipping publishing for call_id='{call_id}'"
            )
            return event, call_id

    log.info(f"{log_prefix} Updating returned recording data for call_id='{call_id}'")
    recordings = []
    for recording in jive_request_recordings:
        filename_encoded = recording["filename"]
        filename = base64.b64decode(recording["filename"]).decode("utf-8")
        ord = dateutil.parser.isoparser().isoparse(filename.split("~", maxsplit=1)[0].split("/")[-1])

        recordings.append([ord, filename, filename_encoded])

    recordings = sorted(recordings, key=lambda r: r[0])
    log.info(f"{log_prefix} Updated returned recording data. recordings='{recordings}' for call_id='{call_id}'")

    log.info(f"{log_prefix} Processing recordings. Persisting them to RDBMS for call_id='{call_id}'")
    for recording in recordings:
        ord = recording[0]
        filename = recording[1]
        filename_encoded = recording[2]

        log.info(f"{log_prefix} Updating Peerlogic call end time and duration for call_id='{call_id}'")
        peerlogic_call = Call.objects.get(pk=call_id)
        peerlogic_call.call_end_time = end_time
        peerlogic_call.duration_seconds = peerlogic_call.call_end_time - peerlogic_call.call_start_time
        peerlogic_call.progress_time_seconds = calculate_progress_time(originator_id=jive_originator_id, end_time=end_time)
        peerlogic_call.connect_duration_seconds = calculate_connect_duration(originator_id=jive_originator_id)
        peerlogic_call.call_connection = CallConnectionTypes.CONNECTED
        peerlogic_call.save()
        log.info(
            f"{log_prefix} Updated Peerlogic call_id='{call_id}' with the following fields: peerlogic_call.call_connection='{peerlogic_call.call_connection}', peerlogic_call.call_end_time='{peerlogic_call.call_end_time}', peerlogic_call.duration_seconds='{peerlogic_call.duration_seconds}'"
        )

        log.info(f"{log_prefix} Creating Peerlogic CallPartial time_interaction_started='{peerlogic_call.call_start_time}' and time_interaction_ended='{ord}'.")

        jive_leg_created_time = event.data_created
        cp = CallPartial.objects.create(call=peerlogic_call, time_interaction_started=jive_leg_created_time, time_interaction_ended=end_time)
        log.info(
            f"{log_prefix} Created Peerlogic CallPartial with cp.id='{cp.id}', peerlogic_call.id='{peerlogic_call.id}', time_interaction_started='{peerlogic_call.call_start_time}' and time_interaction_ended='{end_time}'."
        )

        log.info(f"{log_prefix} Updating event with CallPartial id = cp.id='{cp.id}'")
        event.peerlogic_call_partial_id = cp.id
        event.save()
        log.info(f"{log_prefix} Updated event with CallPartial id = cp.id='{cp.id}'")

        log.info(f"{log_prefix} Publishing leg b ready event for call_id='{call_id}'")
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
        log.info(f"{log_prefix} Published leg b ready event for call_id='{call_id}'")

    return event, call_id


def resync_from_credentials(jive_api_credentials: JiveAPICredentials, request: Request):
    # to avoid timeouts we want to complete execution in 30s
    deadline = datetime.now() + timedelta(seconds=60)
    jive: JiveClient = JiveClient(client_id=settings.JIVE_CLIENT_ID, client_secret=settings.JIVE_CLIENT_SECRET, jive_api_credentials=jive_api_credentials)
    if deadline < datetime.now():
        raise RefreshTokenNoLongerRefreshableException()

    for channel in JiveChannel.objects.filter(jive_api_credentials=jive_api_credentials, active=True):
        log.info(f"Jive: found channel: {channel}")
        # if a channel refresh fails we mark it as inactive
        try:
            log.info(f"Jive: refreshing channel: {channel}")
            jive.refresh_channel_lifetime(channel)
        except:
            log.info(f"Jive: failed to refresh channel {channel.id}, marking as inactive")
            channel.active = False
            channel.save()

    # get the current lines with an active channel for this jive_api_credentials
    line_results = JiveLine.objects.filter(session__channel__jive_api_credentials=jive_api_credentials, session__channel__active=True).values_list(
        "source_jive_id", "source_organization_jive_id"
    )
    current_lines = {Line(r[0], r[1]) for r in line_results}
    external_lines: Set[Line] = set(jive.list_lines_all_users(jive_api_credentials.account_key))

    # compute new lines
    add_lines = external_lines - current_lines
    remove_lines = current_lines - external_lines

    log.info(f"Jive: found {len(add_lines)} new lines and {len(remove_lines)} invalid lines using jive_api_credentials {jive_api_credentials.id}.")

    # delete the removed lines
    JiveLine.objects.filter(source_jive_id__in=remove_lines).delete()

    if add_lines:
        # get the latest active channel for this jive_api_credentials
        channel = (
            JiveChannel.objects.filter(jive_api_credentials=jive_api_credentials, active=True, expires_at__gt=timezone.now()).order_by("-expires_at").first()
        )

        # if no channels are found create one
        if not channel:
            log.info(f"Jive: no active webhook channel found for jive_api_credentials='{jive_api_credentials}', creating one.")
            webhook_url = request.build_absolute_uri(reverse("jive_integration:webhook-receiver"))

            # Jive will only accept a https url so we always replace it, the only case where this would not
            # be an https url is a development environment.
            webhook_url = webhook_url.replace("http://", "https://")

            channel = jive.create_webhook_channel(jive_api_credentials=jive_api_credentials, webhook_url=webhook_url)
            log.info(f"Jive: created channel='{channel}' for jive_api_credentials='{jive_api_credentials}'.")
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

    # record sync event to ensure all jive_api_credentials (formerly called jive_api_credentialss) get a chance to be synced
    # TODO: determine if we should not update this when some channel, session, line or jive_api_credentials has an error
    # It's led to issues understanding staleness of jive_api_credentials because it's ALWAYS updated.
    jive_api_credentials.last_sync = timezone.now()
    jive_api_credentials.save()


def parse_webhook_from_header(header: str) -> str:
    # Example format:
    # 'sig1=("@request-target" "date" "digest");keyid="Webhook.2427ad08-0624-454b-99ce-d05d23f08d0e";alg="hmac-sha256";created=1668543156;expires=1668543456;nonce="/Hny/Qbs+5o="'
    # We need to grab the keyid value
    return header.split('keyid="')[1].split('";alg=')[0]
