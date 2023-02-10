from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from calls.analytics.interactions.models import AgentCallScore, AgentCallScoreMetric
from calls.analytics.interactions.serializers import (
    AgentCallScoreMetricSerializer,
    AgentCallScoreReadSerializer,
    AgentCallScoreWriteSerializer,
)


class AgentCallScoreViewset(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]  # https://peerlogictech.atlassian.net/browse/PTECH-1740
    queryset = AgentCallScore.objects.all().order_by("-modified_at")
    filter_fields = ["metric", "score", "call__id"]

    serializer_class_read = AgentCallScoreReadSerializer
    serializer_class_write = AgentCallScoreWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class AgentCallScoreMetricViewset(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]  # https://peerlogictech.atlassian.net/browse/PTECH-1740
    queryset = AgentCallScoreMetric.objects.all().order_by("-modified_at")
    serializer_class = AgentCallScoreMetricSerializer
    filter_fields = ["group"]
