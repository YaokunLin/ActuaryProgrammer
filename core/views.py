import logging
from typing import Dict

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.setup_user_and_practice import (create_agent, create_user_telecom,
                                          save_user_activity_and_token,
                                          setup_practice, setup_user)

from .models import Client, Patient
from .serializers import ClientSerializer, PatientSerializer

# Get an instance of a logger
log = logging.getLogger(__name__)

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    NETSAPIENS_AUTH_TOKEN_REQUIRED_KEYS = [
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
        except Exception as e:
            log.exception(e)
            return Response(status=netsapiens_access_token_response.status_code, data={"error": e})

        now = timezone.now()

        with transaction.atomic():
            user, user_created = setup_user(now, netsapiens_user)

            save_user_activity_and_token(now, netsapiens_user, user)

            if user_created:
                create_user_telecom(user)
                practice, _ = setup_practice(netsapiens_user["domain"])
                create_agent(user, practice)

        return Response(status=200, data=netsapiens_user)

    def _validate_access_token_response(self, response_json: Dict):
        if not all(key in self.NETSAPIENS_AUTH_TOKEN_REQUIRED_KEYS for key in response_json):
            log.exception("Wrong netsapiens payload to get or create a user")
            raise ValueError("Wrong netsapiens payload to get or create a user")


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
