from django.apps import apps
from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import UserManager as _UserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PracticeManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class UserManager(_UserManager):
    INTROSPECT_TOKEN_PAYLOAD_KEYS = ["token", "client_id", "territory", "domain", "uid", "expires", "scope", "mask_chain"]

    def get_or_create_from_introspect_token_payload(self, payload):
        self.Practice = apps.get_model("core", "Practice")
        self.PracticeTelecom = apps.get_model("core", "PracticeTelecom")
        self._validate_introspect_token_payload(payload)
        uid = payload["uid"]
        domain = payload["domain"]

        practice = self._ensure_related_models_created_from_domain(domain)

        try:
            user = self.get(username=uid)
            user.last_login = timezone.now()
            user.is_active = True
            user.save()
            return user
        except self.model.DoesNotExist:
            self._create_user_and_related_models_from_practice(practice)

        return user

    def _validate_introspect_token_payload(self, payload):
        if not all(key in self.INTROSPECT_TOKEN_PAYLOAD_KEYS for key in payload):
            raise ValueError("Wrong payload to get or create a user")

    def _ensure_related_models_created_from_domain(self, domain: str):

        # Set practice and its telecom record
        practice, created = self.Practice.objects.get_or_create(name=domain)
        if created:
            self.PracticeTelecom.objects.create(domain=domain, practice=practice)

        return practice

    def _create_user_and_related_models_from_practice(self, uid: str):
        try:
            user = self.objects.create(
                username=uid,
                date_joined=timezone.now(),
                last_login=timezone.now(),
                is_active=True,
            )
        # TODO: ERD scaffolding for related models
        # TODO: Add user to Person
        except IntegrityError:
            user = self.objects.get(username=uid)

        return user
