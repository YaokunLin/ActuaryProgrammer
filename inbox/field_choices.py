from django.db import models
from django.utils.translation import gettext_lazy as _


class MessagePriorities(models.TextChoices):
    DEFAULT = "default"
    HIGH = "high"


class BandwidthMessageStatuses(models.TextChoices):
    MESSAGE_DELIVERED = "message-delivered"
    MESSAGE_FAILED = "message-failed"
    MESSAGE_RECEIVED = "message-received"
    MESSAGE_SENDING = "message-sending"

class PeerlogicMessageStatuses(BandwidthMessageStatuses, models.TextChoices):
    BANDWIDTH_MESSAGE_DELIVERED = "bandwidth_message_delivered"
    BANDWIDTH_MESSAGE_FAILED = "bandwidth_message_failed"
    BANDWIDTH_MESSAGE_RECEIVED = "bandwidth_message_received"
    BANDWIDTH_MESSAGE_SENDING = "bandwidth_message_sending"
    MESSAGE_SENT_TO_BANDWIDTH = "message_sent_to_bandwidth"
    MESSAGE_INIT = "message_init"
    # MESSAGE_UNDELIVERED = "message-undelivered"
    # MESSAGE_QUEUED = "queued"


bandwidth_value_to_peerlogic_message_status_map = {
    BandwidthMessageStatuses.MESSAGE_DELIVERED.value: PeerlogicMessageStatuses.BANDWIDTH_MESSAGE_DELIVERED.value,
    BandwidthMessageStatuses.MESSAGE_FAILED.value: PeerlogicMessageStatuses.BANDWIDTH_MESSAGE_FAILED.value,
    BandwidthMessageStatuses.MESSAGE_RECEIVED.value: PeerlogicMessageStatuses.BANDWIDTH_MESSAGE_RECEIVED.value,
    BandwidthMessageStatuses.MESSAGE_SENDING.value: PeerlogicMessageStatuses.BANDWIDTH_MESSAGE_SENDING.value
}
