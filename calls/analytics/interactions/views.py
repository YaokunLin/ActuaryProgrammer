from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, IsAdminUser
from rest_framework.status import HTTP_403_FORBIDDEN

from calls.analytics.interactions.models import AgentCallScore, AgentCallScoreMetric
from calls.analytics.interactions.serializers import (
    AgentCallScoreMetricSerializer,
    AgentCallScoreReadSerializer,
    AgentCallScoreWriteSerializer,
)
from calls.models import Call
from core.models import Agent


class AgentCallScoreViewset(viewsets.ModelViewSet):
    queryset = AgentCallScore.objects.all().order_by("-modified_at")
    filter_fields = ["metric", "score", "call__id"]

    serializer_class_read = AgentCallScoreReadSerializer
    serializer_class_write = AgentCallScoreWriteSerializer

    def dispatch(self, request, *args, **kwargs):
        # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740
        if self.request.user.is_staff or self.request.user.is_superuser or self.request.method in SAFE_METHODS:
            return super().dispatch(request, *args, **kwargs)
        return HttpResponse(PermissionDenied.default_detail, status=403)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740
        queryset = super().get_queryset().prefetch_related("call").filter(call=self.kwargs.get("call_pk"))
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset

        allowed_practice_ids = Agent.objects.filter(user=self.request.user).values_list("practice_id", flat=True)
        if not Call.objects.filter(id=self.kwargs.get("call_pk"), practice_id__in=allowed_practice_ids).exists():
            raise NotFound()

        return queryset


class AgentCallScoreMetricViewset(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740
    queryset = AgentCallScoreMetric.objects.all().order_by("-modified_at")
    serializer_class = AgentCallScoreMetricSerializer
    filter_fields = ["group"]
