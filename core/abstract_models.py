from django.db import models
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


class DateTimeOnlyAuditTrailModel(models.Model):
    """
    Similar to AuditTrailModel, except does not track created_by or modified_by
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True
        get_latest_by = "modified_at"
