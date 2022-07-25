from rest_framework import viewsets
from calls.analytics.interactions.models import AgentCallScore
from calls.analytics.interactions.serializers import AgentCallScoreSerializer


class AgentCallScoreViewset(viewsets.ModelViewSet):
    queryset = AgentCallScore.objects.all().order_by("-modified_at")
    serializer_class = AgentCallScoreSerializer
    filter_fields = ["metric", "score", "call__id"]
