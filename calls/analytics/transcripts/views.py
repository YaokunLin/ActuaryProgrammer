from rest_framework import viewsets

from calls.analytics.transcripts.models import CallSentiment, CallTranscriptFragment, CallTranscriptFragmentSentiment
from calls.analytics.transcripts.serializers import CallSentimentSerializer, CallTranscriptFragmentSerializer, CallTranscriptFragmentSentimentSerializer

class CallSentimentViewset(viewsets.ModelViewSet):
    queryset = CallSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallSentimentSerializer
    filter_fields = ["call__id", "overall_sentiment_score", "caller_sentiment_score", "callee_sentiment_score"]


class CallTranscriptFragmentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSerializer
    # filter_fields =


class CallTranscriptFragmentSentimentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragmentSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSentimentSerializer
    # TODO: filter_fields
