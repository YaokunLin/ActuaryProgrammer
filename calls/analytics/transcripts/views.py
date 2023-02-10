from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

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


class CallSentimentViewset(viewsets.ModelViewSet):
    queryset = CallSentiment.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "overall_sentiment_score", "caller_sentiment_score", "callee_sentiment_score"]

    serializer_class_read = CallSentimentReadSerializer
    serializer_class_write = CallSentimentWriteSerializer
    permission_classes = [IsAdminUser]  # https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # get call to update
            call: Call = Call.objects.get(pk=self.kwargs.get("call_pk"))

            # there should only be one neapt for a call to ensure analytics / counting goes smoothly
            # we err on the side of caution and retrieve all anyway
            call_sentiments = call.call_sentiments.all()
            if call_sentiments.exists():
                call_sentiments.delete()

            # create the new / replacement CallPurpose objects
            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CallTranscriptFragmentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSerializer
    filter_fields = ["call__id", "telecom_persona_type"]
    permission_classes = [IsAdminUser]  # https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class CallTranscriptFragmentSentimentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragmentSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSentimentSerializer
    filter_fields = ["call_transcript_fragment__id", "sentiment_score"]
    permission_classes = [IsAdminUser]  # https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class CallLongestPauseViewset(viewsets.ModelViewSet):
    queryset = CallLongestPause.objects.all().order_by("-modified_at")
    serializer_class = CallLongestPauseSerializer
    filter_fields = ["call__id", "duration"]
    permission_classes = [IsAdminUser]  # https://peerlogictech.atlassian.net/browse/PTECH-1740

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))
