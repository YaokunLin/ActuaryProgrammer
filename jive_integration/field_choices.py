from django.db import models


class JiveEventTypeChoices(models.TextChoices):
    ANNOUNCE = "announce"
    REPLACE = "replace"
    WITHDRAW = "withdraw"
    KEEPALIVE = "keepalive"


class JiveLegStateChoices(models.TextChoices):
    """Keeping uppercase to match events already in the database"""

    CREATED = "CREATED"  # event state when a new leg is created.
    RINGING = "RINGING"  # event state when when a leg begins ringing.
    ANSWERED = "ANSWERED"  # event state when when a leg gets answered.
    BRIDGED = "BRIDGED"  # event state when when a leg gets connected to something.
    UNBRIDGED = "UNBRIDGED"  # event state when when a leg gets disconnected from something.
    HUNGUP = "HUNGUP"  # event state when when an existing leg gets destroyed.
