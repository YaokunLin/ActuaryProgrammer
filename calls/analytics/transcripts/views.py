from rest_framework import viewsets

from calls.analytics.transcripts.models import CallTranscriptFragment, CallTranscriptFragmentSentiment
from calls.analytics.transcripts.serializers import CallTranscriptFragmentSerializer, CallTranscriptFragmentSentimentSerializer


class CallTranscriptFragmentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSerializer
    filter_fields = ["call__id", "telecom_persona_type"]

class CallTranscriptFragmentSentimentViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptFragmentSentiment.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptFragmentSentimentSerializer
    filter_fields = ["call_transcript_fragment__id", "sentiment_score"]
