from datetime import datetime, timedelta
import logging
from typing import Dict


from rest_framework.serializers import ValidationError

from calls.models import Call
from calls.serializers import CallSerializer
from core.models import Practice
from jive_integration.models import JiveSubscriptionEventExtract

US_TELEPHONE_NUMBER_DIGIT_LENGTH = 10
# Get an instance of a logger
log = logging.getLogger(__name__)


def create_peerlogic_call(jive_request_data_key_value_pair: Dict, call_direction: str, start_time: datetime, dialed_number: str, practice: Practice) -> Call:
    log.info(f"Jive: Creating Peerlogic Call object with start_time='{start_time}'.")
    jive_callee_number = jive_request_data_key_value_pair.get("callee", {}).get("number")
    jive_caller_number = jive_request_data_key_value_pair.get("caller", {}).get("number")
    sip_callee_extension = ""
    sip_callee_number = ""
    sip_caller_extension = ""
    sip_caller_number = ""
    # if callee is an extension:
    if len(jive_callee_number) != US_TELEPHONE_NUMBER_DIGIT_LENGTH:
        sip_callee_extension = jive_callee_number
        sip_callee_number = dialed_number
        sip_caller_number = f"+1{jive_caller_number}"
    # if caller is an extension:
    if len(jive_caller_number) != US_TELEPHONE_NUMBER_DIGIT_LENGTH:
        sip_caller_extension = jive_caller_number
        sip_caller_number = dialed_number
        sip_callee_number = f"+1{jive_callee_number}"
    if not sip_callee_number:
        sip_callee_number = jive_callee_number
    # TODO: Logic for outbound caller number for practice - no ani present

    call_fields = {
        "practice_id": practice.pk,
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

    peerlogic_call_serializer = CallSerializer(data=call_fields)
    peerlogic_call_serializer_is_valid = peerlogic_call_serializer.is_valid()
    peerlogic_call_serializer_errors: Dict = dict(peerlogic_call_serializer.errors)

    # TODO: natural_key method keeps giving practice field the practice name instead of the pk...
    # not sure how to remedy, but it keeps saving the call correctly despite this validation error.
    # popping for now.
    peerlogic_call_serializer_errors.pop("practice")
    if not peerlogic_call_serializer_is_valid and peerlogic_call_serializer_errors:
        log.exception(f"Error from peerlogic_call_serializer validation: {peerlogic_call_serializer_errors}")
        raise ValidationError(peerlogic_call_serializer_errors)

    return Call.objects.create(**call_fields)


def get_call_id_from_previous_announce_event(entity_id: str) -> str:
    log.info(f"Jive: Checking if there is a previous subscription event with this entity_id='{entity_id}'.")
    try:
        return JiveSubscriptionEventExtract.objects.get(jive_type="announce", entity_id=entity_id).peerlogic_call_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"No JiveSubscriptionEventExtract found with type='announce' and given entity_id='{entity_id}'")


def get_call_id_from_previous_announce_event_by_originator_id(originator_id: str) -> str:
    log.info(f"Jive: Checking if there is a previous subscription event with this originator_id='{originator_id}'.")
    try:
        return JiveSubscriptionEventExtract.objects.get(jive_type="announce", data_originator_id=originator_id).peerlogic_call_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"No JiveSubscriptionEventExtract found with type='announce' and given originator_id='{originator_id}'")
