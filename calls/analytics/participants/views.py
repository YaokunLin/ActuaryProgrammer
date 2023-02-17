from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from calls.analytics.intents.views import (
    CallParentDeleteChildrenOnCreateMixin,
    CallParentQueryFilterMixin,
)
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


class AgentEngagedWithViewset(CallParentQueryFilterMixin, CallParentDeleteChildrenOnCreateMixin, viewsets.ModelViewSet):
    queryset = AgentEngagedWith.objects.all().order_by("-modified_at")
    serializer_class_read = AgentEngagedWithReadSerializer
    serializer_class_write = AgentEngagedWithWriteSerializer
    filter_fields = ["non_agent_engagement_persona_type", "call__id"]
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740

    _CHILD_METHOD_NAME = "engaged_in_calls"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read
