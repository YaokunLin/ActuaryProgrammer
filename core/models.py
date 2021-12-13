from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import AbstractUser, Permission, UserManager as _UserManager, _user_get_permissions, _user_has_perm, _user_has_module_perms
from django.db.models.fields.related import ForeignKey
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_userforeignkey.models.fields import UserForeignKey
from django_extensions.db.fields import ShortUUIDField

from phonenumber_field.modelfields import PhoneNumberField

from core.field_choices import ClientTypes, IndustryTypes
from core.managers import PracticeManager, UserManager




class Practice(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    name = models.CharField(_("name"), max_length=150, unique=True)
    industry = models.CharField(choices=IndustryTypes.choices, default=IndustryTypes.DENTISTRY_GENERAL, max_length=250)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
    )

    objects = PracticeManager()

    class Meta:
        verbose_name = _("practice")
        verbose_name_plural = _("practices")

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    objects = PracticeManager()


class UserPerson(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    name = models.CharField(_("name"), max_length=300, unique=True)
    practice_id =  ForeignKey(
        
    )
    user_id = ShortUUIDField(editable=False)

class PermissionsMixin(models.Model):
    """
    Add the fields and methods necessary to support the Practice and Permission
    models using the ModelBackend.
    """

    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_("Designates that this user has all permissions without " "explicitly assigning them."),
    )
    practices = models.ManyToManyField(
        Practice,
        verbose_name=_("practices"),
        through="core.UserPerson"
        blank=True,
        help_text=_("The practices this user belongs to. A user will get all permissions " "granted to each of their practices."),
        related_name="user_set",
        related_query_name="user",
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

    def get_practice_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has through their
        practices. Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, "practice")

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

class Person(PermissionsMixin):
    id = ShortUUIDField(primary_key=True, editable=False)
    name = models.CharField(_("name"), max_length=300, unique=True)


class PracticePerson(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    practice_id = ShortUUIDField(editable=False)

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


class User(AbstractUser, PermissionsMixin):
    id = ShortUUIDField(primary_key=True, editable=False)
    # Using plain "name" here since we may not have it broken out into
    # first and last
    name = models.CharField(_("name"), max_length=300, blank=True)
    objects = UserManager()


class UserTelecom(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    phone_sms = PhoneNumberField(blank=True)
    phone_callback = PhoneNumberField(blank=True)

    # TODO: Strip off the prefix in User model's username
    @property
    def telecom_user(self):
        """Often a 4-6 digit user extension"""
        return ""


class Client(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    client_type = models.CharField(choices=ClientTypes.choices, max_length=50, default=ClientTypes.PRACTICE_MANAGEMENT_SOFTWARE)
    practice = models.OneToOneField(Practice, on_delete=models.CASCADE)
    rest_base_url = models.CharField(max_length=300)  # Can be Dentrix, another EMR, or some other system


class PracticeTelecom(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    practice = models.OneToOneField(Practice, on_delete=models.CASCADE)
    domain = models.CharField(max_length=80, db_index=True)
    phone_sms = PhoneNumberField(blank=True)
    phone_callback = PhoneNumberField(blank=True)


class Patient(AuditTrailModel):
    def velox_extract_data_default():
        return {}

    id = ShortUUIDField(primary_key=True, editable=False)
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
    velox_extract_data = models.JSONField(default=velox_extract_data_default)
