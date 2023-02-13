from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from calls.analytics.participants.models import AgentAssignedCall, AgentEngagedWith
from calls.analytics.participants.serializers import (
    AgentAssignedCallSerializer,
    AgentEngagedWithReadSerializer,
    AgentEngagedWithWriteSerializer,
)
from calls.models import Call


class AgentAssignedCallViewSet(viewsets.ModelViewSet):
    queryset = AgentAssignedCall.objects.all().order_by("-modified_at")
    serializer_class = AgentAssignedCallSerializer
    filter_fields = ["agent__id", "call__id"]
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740


class AgentEngagedWithViewset(viewsets.ModelViewSet):
    queryset = AgentEngagedWith.objects.all().order_by("-modified_at")
    serializer_class_read = AgentEngagedWithReadSerializer
    serializer_class_write = AgentEngagedWithWriteSerializer
    filter_fields = ["non_agent_engagement_persona_type", "call__id"]
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        return super().get_queryset().filter(call_id=self.kwargs.get("call_pk"))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # get call to update
            call: Call = Call.objects.get(pk=self.kwargs.get("call_pk"))

            # there should only be one neapt for a call to ensure analytics / counting goes smoothly
            # we err on the side of caution and retrieve all anyway
            engaged_in_calls = call.engaged_in_calls.all()
            if engaged_in_calls.exists():
                engaged_in_calls.delete()

            # create the new / replacement CallPurpose objects
            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
