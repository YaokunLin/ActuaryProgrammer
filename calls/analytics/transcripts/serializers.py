from rest_framework import serializers

from calls.analytics.transcripts.models import (
    CallLongestPause,
    CallSentiment,
    CallTranscriptFragment,
    CallTranscriptFragmentSentiment,
)


class CallSentimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallSentiment
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


# TODO: InlineCallTranscriptFragmentSentimentSerializer


class CallTranscriptFragmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallTranscriptFragment
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallTranscriptFragmentSentimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallTranscriptFragmentSentiment
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallLongestPauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLongestPause
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
