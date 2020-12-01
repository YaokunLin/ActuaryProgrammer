import uuid
import datetime

from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as _UserManager
from django.utils import timezone

from django_userforeignkey.models.fields import UserForeignKey

class AuditTrailModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)
    created_by = UserForeignKey(
        on_delete=models.SET_NULL,
        auto_user_add=True,
        verbose_name="The user that is automatically assigned",
        related_name="%(class)s_created",
        blank=True,
        null=True,
    )
    modified_by = UserForeignKey(
        on_delete=models.SET_NULL,
        auto_user_add=True,
        verbose_name="The user that is automatically assigned",
        related_name="%(class)s_modified",
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True
        get_latest_by = "modified_at"


class UserManager(_UserManager):
    def get_or_create_for_communications_platform(self, payload):
        uid = payload["uid"]

        try:
            user = self.get(uid=uid)
            user.last_login = timezone.now()
            user.is_active = True
            user.save()
        except self.model.DoesNotExist:
            pass

        try:
            user = self.create(
                uid=uid,
                username=payload["username"],
                email=payload["user_email"],
                name=payload["displayName"],
                domain=payload["domain"],
                date_joined=timezone.now(),
                last_login=timezone.now(),
                is_active=True,
            )
        except IntegrityError:
            user = self.get(uid=uid)

        return user


class User(AbstractUser):
    uid = models.CharField(max_length=128, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)
    user= models.CharField(max_length=80, blank=True)
    email = models.CharField(max_length=128, blank=True, unique=True)
    name = models.CharField(max_length=256, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "uid"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.name
