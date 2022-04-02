from rest_framework import viewsets

from calls.analytics.transcripts.models import CallLongestPause, CallTranscriptFragment, CallTranscriptFragmentSentiment
from calls.analytics.transcripts.serializers import CallLongestPauseSerializer, CallTranscriptFragmentSerializer, CallTranscriptFragmentSentimentSerializer


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
    filter_fields = ["call__id", "is_longest", "duration"]
