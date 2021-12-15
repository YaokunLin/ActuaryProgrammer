from django.utils import timezone
from typing import Dict, Tuple
from django.utils import timezone

from .models import Person, Practice, PracticePerson, PracticeTelecom, User, UserPerson, UserTelecom


def setup_practice(domain: str):

    # Set practice and its telecom record
    practice, created = Practice.objects.get_or_create(name=domain)
    if created:
        create_practice_telecom(domain=domain, practice=practice)

    return (practice, created)


def create_practice_telecom(domain: str, practice: Practice):
    practice_telecom, created = PracticeTelecom.objects.get_or_create(domain=domain, practice=practice)
    # TODO: associate telephone number and sms number from netsapiens
    return (practice_telecom, created)


def associate_person_to_practice(person: Person, practice: Practice):
    return PracticePerson.objects.get_or_create(person=person, practice=practice)


def create_person_for_user(user: User) -> Person:
    person, created = Person.objects.get_or_create(name=user.name)
    user_person, created = UserPerson.objects.get_or_create(user=user, person=person)

    return (person, created)


def setup_user(netsapiens_user: Dict[str, str]) -> Tuple[User, bool]:
    username = netsapiens_user["username"]
    name = netsapiens_user["displayName"]
    email = netsapiens_user["user_email"]
    access_token = netsapiens_user["access_token"]
    refresh_token = netsapiens_user["refresh_token"]
    now = timezone.now()
    print(now)
    token_expiry = now + timezone.timedelta(seconds=netsapiens_user["expires_in"])
    print(token_expiry)
    is_staff = False
    if netsapiens_user["domain"] == "Peerlogic":
        is_staff = True

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "name": name,
            "email": email,
            "is_staff": is_staff,
            "date_joined": now,
        },
    )

    # user activity
    user.is_active = True
    user.last_login = now

    # token info
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_expiry = token_expiry

    user.save()

    return (
        user,
        created,
    )


def create_user_telecom(user: User):
    user_telecom, created = UserTelecom.objects.get_or_create(user=user)
    # TODO: associate telephone number and sms number from netsapiens
    return (user_telecom, created)
