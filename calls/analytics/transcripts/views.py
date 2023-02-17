from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from calls.analytics.intents.views import (
    CallParentDeleteChildrenOnCreateMixin,
    CallParentQueryFilterMixin,
)
from calls.analytics.transcripts.models import (
    CallLongestPause,
    CallSentiment,
    CallTranscriptFragment,
    CallTranscriptFragmentSentiment,
)
from calls.analytics.transcripts.serializers import (
    CallLongestPauseSerializer,
    CallSentimentReadSerializer,
    CallSentimentWriteSerializer,
    CallTranscriptFragmentSentimentSerializer,
    CallTranscriptFragmentSerializer,
)
from calls.models import Call


class CallSentimentViewset(CallParentQueryFilterMixin, CallParentDeleteChildrenOnCreateMixin, viewsets.ModelViewSet):
    queryset = CallSentiment.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "overall_sentiment_score", "caller_sentiment_score", "callee_sentiment_score"]

    serializer_class_read = CallSentimentReadSerializer
    serializer_class_write = CallSentimentWriteSerializer
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740

    _CHILD_METHOD_NAME = "call_sentiments"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read


class CallTranscriptFragmentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSerializer
    filter_fields = ["call__id", "telecom_persona_type"]
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class CallTranscriptFragmentSentimentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragmentSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSentimentSerializer
    filter_fields = ["call_transcript_fragment__id", "sentiment_score"]
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class CallLongestPauseViewset(viewsets.ModelViewSet):
    queryset = CallLongestPause.objects.all().order_by("-modified_at")
    serializer_class = CallLongestPauseSerializer
    filter_fields = ["call__id", "duration"]
    permission_classes = [IsAdminUser]  # TODO: https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))
