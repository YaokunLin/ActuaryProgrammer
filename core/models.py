from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, _user_get_permissions, _user_has_perm, _user_has_module_perms

from django.utils.translation import gettext_lazy as _

from django_extensions.db.fields import ShortUUIDField

from phonenumber_field.modelfields import PhoneNumberField

from core.abstract_models import AuditTrailModel
from core.field_choices import IndustryTypes, VoipProviderIntegrationTypes
from core.managers import PracticeManager, UserManager

# This is to mimick Django's permissions mixin
# Don't change this mixin unless you know what you're doing :)
class PermissionsMixin(AuditTrailModel):
    """
    Add the fields and methods necessary to support the Practice and Permission
    models using the ModelBackend.
    """

    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_("Designates that this user has all permissions without " "explicitly assigning them."),
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="user_set",
        related_query_name="user",
    )

    class Meta:
        abstract = True

    def get_user_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has directly.
        Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, "user")

    # TODO: get practice subscription perms when available

    def get_all_permissions(self, obj=None):
        return _user_get_permissions(self, obj, "all")

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Return True if the user has each of the specified permissions. If
        object is passed, check if the user has all required perms for it.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        """
        Return True if the user has any permissions in the given app label.
        Use similar logic as has_perm(), above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)


class User(AbstractUser, PermissionsMixin):
    id = ShortUUIDField(primary_key=True, editable=False)
    groups = None
    # Using plain "name" here since we may not have it broken out into
    # first and last
    name = models.CharField(_("name"), max_length=300, blank=True)
    access_token = models.CharField(max_length=128, blank=True)
    refresh_token = models.CharField(max_length=128, blank=True)
    token_expiry = models.DateTimeField(null=True)
    objects = UserManager()


class UserTelecom(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(_("username"), max_length=150, unique=True)
    phone_sms = PhoneNumberField(blank=True)
    phone_callback = PhoneNumberField(blank=True)

    @property
    def telecom_user(self):
        """Often a 4-6 digit user extension"""
        return self.username.split("@")[0]


class Practice(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    name = models.CharField(_("name"), max_length=150, unique=True)
    industry = models.CharField(choices=IndustryTypes.choices, default=IndustryTypes.DENTISTRY_GENERAL, max_length=250)

    objects = PracticeManager()

    class Meta:
        verbose_name = _("practice")
        verbose_name_plural = _("practices")

    def __str__(self):
        return self.name

    # This is to mimick Django's group model
    def natural_key(self):
        return (self.name,)

    objects = PracticeManager()


class Agent(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    practice = models.ForeignKey(Practice, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id} - {self.user.name}"


class Client(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    description = models.CharField(max_length=300)
    practice = models.OneToOneField(Practice, on_delete=models.CASCADE)
    rest_base_url = models.CharField(max_length=300)  # Can be Dentrix, another EMR, or some other system


class PracticeTelecom(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    practice = models.OneToOneField(Practice, on_delete=models.CASCADE)
    domain = models.CharField(max_length=80, db_index=True)
    phone_sms = PhoneNumberField(blank=True)
    phone_callback = PhoneNumberField(blank=True)


class Patient(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    practice = models.ForeignKey(Practice, on_delete=models.CASCADE)
    name_first = models.CharField(blank=True, max_length=255, db_index=True)
    name_last = models.CharField(blank=True, max_length=255, db_index=True)
    placeholder = models.CharField(blank=True, max_length=255)
    phone_mobile = PhoneNumberField(db_index=True, blank=True, null=False, default="")
    phone_home = PhoneNumberField(db_index=True, blank=True, null=False, default="")
    phone_work = PhoneNumberField(db_index=True, blank=True, null=False, default="")
    phone_fax = PhoneNumberField(blank=True, null=False, default="")
    address_line_1 = models.CharField(blank=True, max_length=255)
    address_line_2 = models.CharField(blank=True, max_length=255)
    zip_code = models.CharField(max_length=50)
    zip_code_add_on = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateTimeField()


class UserPatient(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)


class VoipProvider(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    company_name = models.CharField(max_length=160)  # e.g. OIT Services
    integration_type = models.CharField(max_length=150, choices=VoipProviderIntegrationTypes.choices, default=VoipProviderIntegrationTypes.NETSAPIENS)

    active = models.BooleanField(null=True, blank=False, default=False)  # whether this integrator is active and we can receive events from them
