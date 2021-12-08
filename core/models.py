from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import AbstractUser, Permission, UserManager as _UserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_userforeignkey.models.fields import UserForeignKey
from django_extensions.db.fields import ShortUUIDField

from phonenumber_field.modelfields import PhoneNumberField

from core.field_choices import ClientTypes
from core.managers import PracticeManager, UserManager

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


class User(AbstractUser):
    id = ShortUUIDField(primary_key=True, editable=False)
    # Using plain "name" here since we may not have it broken out into
    # first and last
    name = models.CharField(_("name"), max_length=300, blank=True)
    telecom_user = models.CharField(_("telecom user (not sip username)"), max_length=80, blank=True)
    objects = UserManager()


class PracticePerson(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    user = models.OneToOneField("User", on_delete=models.CASCADE)


class Practice(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    name = models.CharField(_("name"), max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
    )

    objects = PracticeManager()


class Client(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    client_type = models.CharField(choices=ClientTypes.choices, max_length=50, default=ClientTypes.PRACTICE_MANAGEMENT_SOFTWARE)
    practice = models.OneToOneField(Practice, on_delete=models.CASCADE)
    rest_base_url = models.CharField(max_length=300)  # Can be Dentrix, another EMR, or some other system


class PracticeTelecom(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    practice = models.OneToOneField(Practice, on_delete=models.CASCADE)
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
