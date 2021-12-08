from django.db import models


class ClientTypes(models.TextChoices):
    PRACTICE_MANAGEMENT_SOFTWARE = "pms"