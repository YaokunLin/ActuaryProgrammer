import uuid
import datetime

from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import AbstractUser, Group, UserManager as _UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_userforeignkey.models.fields import UserForeignKey
from django_extensions.db.fields import ShortUUIDField


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
    def get_or_create_for_user(self, payload):
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
                date_joined=timezone.now(),
                last_login=timezone.now(),
                is_active=True,
            )
        except IntegrityError:
            user = self.get(uid=uid)

        return user


class User(AbstractUser):
    # Using plain "name" here since we may not have it broken out into
    # first and last
    name = models.CharField(_("name"), max_length=300, blank=True)
    telecom_user = models.CharField(
        _("telecom user (not sip username)"), max_length=80, blank=True
    )
    access_token = models.CharField(
        _("telecom access token"), max_length=255, blank=True
    )
    refresh_token = models.CharField(
        _("telecom refresh token"), max_length=255, blank=True
    )
    expires_at = models.DateTimeField(_("telecom token expires at"), null=True)
    sms_number = models.CharField(max_length=10, blank=True)


class Client(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    rest_base_url = (
        models.URLField()
    )  # Can be Dentrix, another EMR, or some other system
