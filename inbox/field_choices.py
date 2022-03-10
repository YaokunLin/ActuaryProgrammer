from django.db import models
from django.utils.translation import gettext_lazy as _


class MessagePriorities(models.TextChoices):
    DEFAULT = "default"
    HIGH = "high"


class MessageStatuses(models.TextChoices):
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    FAILED = "failed"
    QUEUED = "queued"
    RECEIVED = "received"
    SENDING = "sending"
    SENT = "sent"
    UNDELIVERED = "undelivered"
