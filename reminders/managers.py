from django.db import models


class CadenceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related("user_sending_reminder", "client")
