import logging
from jive_integration.models import JiveSubscriptionEventExtract

# Get an instance of a logger
log = logging.getLogger(__name__)


def get_call_id_from_previous_announce_event(entity_id: str) -> str:
    try:
        return JiveSubscriptionEventExtract.objects.get(type="announce", entity_id=entity_id).peerlogic_call_id
    except JiveSubscriptionEventExtract.DoesNotExist:
        log.info(f"No JiveSubscriptionEventExtract found with type='announce' and given entity_id='{entity_id}'")


def is_first_withdraw_event(entity_id: str) -> str:
    try:
        JiveSubscriptionEventExtract.objects.get(type="withdraw", entity_id=entity_id)
        return False
    except JiveSubscriptionEventExtract.DoesNotExist:
        return True
