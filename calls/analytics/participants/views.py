from rest_framework import viewsets

from calls.analytics.participants.models import (
    AgentAssignedCall,
    AgentEngagedWith,
)
from calls.analytics.participants.serializers import (
    AgentAssignedCallSerializer,
    AgentEngagedWithSerializer,
)


class AgentAssignedCallViewSet(viewsets.ModelViewSet):
    queryset = AgentAssignedCall.objects.all().order_by("-modified_at")
    serializer_class = AgentAssignedCallSerializer
    filter_fields = ["agent", "call__id"]


class AgentEngagedWithViewset(viewsets.ModelViewSet):
    queryset = AgentEngagedWith.objects.all().order_by("-modified_at")
    serializer_class = AgentEngagedWithSerializer
    filter_fields = ["non_agent_engagement_persona_type", "call__id"]
