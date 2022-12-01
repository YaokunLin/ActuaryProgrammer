from typing import Any, Optional

from django.apps import apps
from django.contrib.auth.models import UserManager as _UserManager
from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PracticeManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class UserManager(_UserManager):
    """
    Continues to be necessary for leveraging the Netsapiens credentials for legacy login of cloud functions and our own API. Holy fuck. 2022-08-05"""

    INTROSPECT_TOKEN_PAYLOAD_KEYS = ["token", "client_id", "territory", "domain", "uid", "expires", "scope", "mask_chain"]

    def get_and_update_from_introspect_token_payload(self, payload) -> Optional[Any]:
        self._validate_introspect_token_payload(payload)
        uid = payload["uid"]

        try:
            # this would generally be an get_or_create since we call this message after successful authentication, so a user SHOULD BE in our system
            # however, we are only creating users during our login operation for the time being to provide a single entrypoint for user creation
            # why? because an external system (netsapiens) is currently involved in authentication and we want to minimize code surface area that trusts it
            user = self.get(username=uid)
            user.last_login = timezone.now()
            user.is_active = True
            user.save()
            return user
        except self.model.DoesNotExist:
            pass  # you shall not pass

        return None

    def _validate_introspect_token_payload(self, payload) -> None:
        if not all(key in self.INTROSPECT_TOKEN_PAYLOAD_KEYS for key in payload):
            raise ValueError("Wrong payload to get or create a user")
