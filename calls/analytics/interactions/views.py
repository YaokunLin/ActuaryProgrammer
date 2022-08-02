from rest_framework import viewsets
from calls.analytics.interactions.models import AgentCallScore
from calls.analytics.interactions.serializers import AgentCallScoreReadSerializer, AgentCallScoreWriteSerializer


class AgentCallScoreViewset(viewsets.ModelViewSet):
    queryset = AgentCallScore.objects.all().order_by("-modified_at")
    filter_fields = ["metric", "score", "call__id"]

    serializer_class_read = AgentCallScoreReadSerializer
    serializer_class_write = AgentCallScoreWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read    
