from rest_framework import viewsets

from calls.analytics.participants.models import (
    AgentAssignedCall,
    AgentEngagedWith,
)
from calls.analytics.participants.serializers import (
    AgentAssignedCallSerializer,
    AgentEngagedWithReadSerializer,
    AgentEngagedWithWriteSerializer,
)


class AgentAssignedCallViewSet(viewsets.ModelViewSet):
    queryset = AgentAssignedCall.objects.all().order_by("-modified_at")
    serializer_class = AgentAssignedCallSerializer
    filter_fields = ["agent__id", "call__id"]


class AgentEngagedWithViewset(viewsets.ModelViewSet):
    queryset = AgentEngagedWith.objects.all().order_by("-modified_at")
    serializer_class_read = AgentEngagedWithReadSerializer
    serializer_class_write = AgentEngagedWithWriteSerializer
    filter_fields = ["non_agent_engagement_persona_type", "call__id"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))
