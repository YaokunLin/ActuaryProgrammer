from django.db import models

class JiveEventTypes(models.TextChoices):
    ANNOUNCE = "announce"
    REPLACE = "replace"
    WITHDRAW = "withdraw"

class JiveEventState(models.TextChoices):
    RINGING = "ringing"
    ANSWERED = "answered"
    HUNGUP = "hungup"