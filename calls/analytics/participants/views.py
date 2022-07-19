from rest_framework import viewsets
from calls.analytics.participants.models import (
    AgentEngagedWith,
)

from calls.analytics.participants.serializers import (
    AgentEngagedWithSerializer,
)


class AgentEngagedWithViewset(viewsets.ModelViewSet):
    queryset = AgentEngagedWith.objects.all().order_by("-modified_at")
    serializer_class = AgentEngagedWithSerializer
    filter_fields = ["non_agent_engagement_persona_type", "call__id"]
