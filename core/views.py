from typing import Dict, Tuple
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import render

from rest_framework.permissions import AllowAny
from rest_framework import authentication, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Client, Patient, Person, Practice, PracticePerson, PracticeTelecom, User, UserPerson, UserTelecom
from .netsapiens import netsapiens_auth_token_from_response
from .serializers import ClientSerializer, PatientSerializer


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
    is_staff = False
    if netsapiens_user["domain"] == "Peerlogic":
        is_staff = True

    user, created = User.objects.get_or_create(
        username=username,
        defaults={"name": name, "email": email, "is_staff": is_staff, "date_joined": timezone.now(), "last_login": timezone.now(), "is_active": True},
    )

    return (
        user,
        created,
    )


def create_user_telecom(user: User):
    user_telecom, created = UserTelecom.objects.get_or_create(user=user)
    # TODO: associate telephone number and sms number from netsapiens
    return (user_telecom, created)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    NETSAPIENS_AUTH_TOKEN_RESPONSE_KEYS = [
        "username",
        "user",
        "territory",
        "domain",
        "site",
        "group",
        "uid",
        "scope",
        "user_email",
        "displayName",
        "access_token",
        "expires_in",
        "token_type",
        "refresh_token",
        "client_id",
        "apiversion",
    ]

    def post(self, request, format=None):
        try:
            netsapiens_access_token_response = settings.NETSAPIENS_SYSTEM_CLIENT.request("POST", settings.NETSAPIENS_ACCESS_TOKEN_URL, data=request.data)
            netsapiens_access_token_response.raise_for_status()
            netsapiens_user = netsapiens_access_token_response.json()
            self._validate_access_token_response(netsapiens_user)
            print(netsapiens_user)
        except:
            return Response(status=netsapiens_access_token_response.status_code)

        user, user_created = setup_user(netsapiens_user)
        print("in post")
        print(user)
        # TODO: put back flag
        if user_created:
            create_user_telecom(user)
            person, _ = create_person_for_user(user)
            practice, _ = setup_practice(netsapiens_user["domain"])
            associate_person_to_practice(person, practice)

        return Response(status=200, data=netsapiens_user)

    def _validate_access_token_response(self, response_json: Dict):
        if not all(key in self.NETSAPIENS_AUTH_TOKEN_RESPONSE_KEYS for key in response_json):
            raise ValueError("Wrong payload to get or create a user")


class ClientViewset(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = Client.objects.all()
        practice_name = self.request.query_params.get("practice_name", None)
        if practice_name is not None:
            queryset = queryset.filter(practice__name=practice_name)
        return queryset


class PatientViewset(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

    filterset_fields = ["phone_mobile", "phone_home", "phone_work", "phone_fax"]
    search_fields = ["name_first", "name_last", "phone_mobile", "phone_home", "phone_work"]
