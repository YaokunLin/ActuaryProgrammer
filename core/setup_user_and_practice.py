from typing import Dict, Tuple

from django.conf import settings
from django.utils import timezone

from .models import Agent, Practice, PracticeTelecom, User, UserTelecom


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


def setup_user(login_time: timezone, netsapiens_user: Dict[str, str]) -> Tuple[User, bool]:
    username = netsapiens_user["username"]
    name = netsapiens_user["displayName"]
    email = netsapiens_user["user_email"]
    is_staff = netsapiens_user["domain"] == settings.IS_STAFF_TELECOM_DOMAN

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


def save_user_activity_and_token(login_time: timezone, netsapiens_user: Dict[str, str], user: User) -> User:
    access_token = netsapiens_user["access_token"]
    refresh_token = netsapiens_user["refresh_token"]
    token_expiry = login_time + timezone.timedelta(seconds=netsapiens_user["expires_in"])

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
