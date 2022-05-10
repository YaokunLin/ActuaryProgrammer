from datetime import datetime
import logging
from typing import Dict, Tuple

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Agent, Practice, PracticeTelecom, User, UserTelecom


# Get an instance of a logger
log = logging.getLogger(__name__)


def setup_practice(domain: str) -> Tuple[Practice, bool]:

    # Set practice and its telecom record
    practice, created = Practice.objects.get_or_create(name=domain)
    if created:
        create_practice_telecom(domain=domain, practice=practice)

    return (practice, created)


def create_practice_telecom(domain: str, practice: Practice):
    practice_telecom, created = PracticeTelecom.objects.get_or_create(domain=domain, practice=practice)
    # TODO: associate telephone number and sms number from netsapiens
    return (practice_telecom, created)


def setup_user(username: str, name: str, email: str, domain: str, login_time: timezone) -> Tuple[User, bool]:
    is_staff = domain == settings.IS_STAFF_TELECOM_DOMAIN

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "name": name,
            "email": email,
            "is_staff": is_staff,
            "date_joined": login_time,
        },
    )
    return (
        user,
        created,
    )


def update_user_on_refresh(username: str, login_time: timezone) -> User:
    try:
        user = get_object_or_404(User, username=username)
        user.last_login = login_time
        user.save()
    except MultipleObjectsReturned as mor:
        msg = "Error occurred identifying user by refresh token. Please contact the system administrator."
        raise ValueError(msg)

    return user


def save_user_activity_and_token(access_token: str, refresh_token: str, expires_in_seconds: int, login_time: timezone, user: User) -> User:
    token_expiry = login_time + timezone.timedelta(seconds=expires_in_seconds)

    # user activity
    user.is_active = True
    user.last_login = login_time

    # token info
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_expiry = token_expiry

    user.save()

    return user


def create_user_telecom(user: User) -> Tuple[UserTelecom, bool]:
    user_telecom, created = UserTelecom.objects.get_or_create(user=user, username=user.username)
    # TODO: associate telephone number and sms number from netsapiens
    return (user_telecom, created)


def create_agent(user: str, practice: Practice) -> Tuple[Agent, bool]:
    agent, created = Agent.objects.get_or_create(user=user, practice=practice)
    return (agent, created)
