from rest_framework import viewsets

from calls.analytics.transcripts.models import (
    CallLongestPause,
    CallSentiment,
    CallTranscriptFragment,
    CallTranscriptFragmentSentiment,
)
from calls.analytics.transcripts.serializers import (
    CallLongestPauseSerializer,
    CallSentimentSerializer,
    CallTranscriptFragmentSerializer,
    CallTranscriptFragmentSentimentSerializer,
)


class CallSentimentViewset(viewsets.ModelViewSet):
    queryset = CallSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallSentimentSerializer
    filter_fields = ["call__id", "overall_sentiment_score", "caller_sentiment_score", "callee_sentiment_score"]


class CallTranscriptFragmentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSerializer
    filter_fields = ["call__id", "telecom_persona_type"]


class CallTranscriptFragmentSentimentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragmentSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSentimentSerializer
    filter_fields = ["call_transcript_fragment__id", "sentiment_score"]


class CallLongestPauseViewset(viewsets.ModelViewSet):
    queryset = CallLongestPause.objects.all().order_by("-modified_at")
    serializer_class = CallLongestPauseSerializer
    filter_fields = ["call__id", "duration"]
