from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import AbstractUser, Group, UserManager as _UserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_userforeignkey.models.fields import UserForeignKey
from django_extensions.db.fields import ShortUUIDField

from phonenumber_field.modelfields import PhoneNumberField


class AuditTrailModel(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
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
    INTROSPECT_TOKEN_PAYLOAD_KEYS = ["token", "client_id", "territory", "domain", "uid", "expires", "scope", "mask_chain"]

    def get_or_create_from_introspect_token_payload(self, payload):
        self._validate_introspect_token_payload(payload)
        uid = payload["uid"]

        try:
            user = self.get(username=uid)
            user.last_login = timezone.now()
            user.is_active = True
            user.save()
            return user
        except self.model.DoesNotExist:
            pass

        # Set group domain
        group, created = Group.objects.get_or_create(name=payload["domain"])
        if not created:
            raise ValueError("Group not created - cannot create user")

        try:
            user = self.create(
                username=uid,
                date_joined=timezone.now(),
                last_login=timezone.now(),
                is_active=True,
            )
            group.user_set.add(user)
        except IntegrityError:
            user = self.get(username=uid)

        return user

    def _validate_introspect_token_payload(self, payload):
        if not all(key in self.INTROSPECT_TOKEN_PAYLOAD_KEYS for key in payload):
            raise ValueError("Wrong payload to get or create a user")


class User(AbstractUser):
    # Using plain "name" here since we may not have it broken out into
    # first and last
    name = models.CharField(_("name"), max_length=300, blank=True)
    telecom_user = models.CharField(_("telecom user (not sip username)"), max_length=80, blank=True)
    objects = UserManager()


class Client(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    rest_base_url = models.URLField()  # Can be Dentrix, another EMR, or some other system


class GroupTelecom(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    sms_number = PhoneNumberField(blank=True)


class Contact(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    first_name = models.CharField(blank=True, max_length=255)
    last_name = models.CharField(blank=True, max_length=255)
    placeholder = models.CharField(blank=True, max_length=255)
    mobile_number = PhoneNumberField()
    fax_number = PhoneNumberField(blank=True)
    address_line_1 = models.CharField(blank=True, max_length=255)
    address_line_2 = models.CharField(blank=True, max_length=255)
    zip_code = models.CharField(max_length=50)
    zip_code_add_on = models.CharField(max_length=50, blank=True)
