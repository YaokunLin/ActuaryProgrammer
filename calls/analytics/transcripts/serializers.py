from rest_framework import serializers

from calls.analytics.transcripts.models import (
    CallLongestPause,
    CallSentiment,
    CallTranscriptFragment,
    CallTranscriptFragmentSentiment,
)
from calls.models import Call
from calls.serializers import CallNestedRouterBaseWriteSerializerMixin


class CallSentimentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallSentiment
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallSentimentWriteSerializer(CallNestedRouterBaseWriteSerializerMixin, serializers.ModelSerializer):
    def create(self, validated_data):
        # get call and its id so that the payload doesn't need to specify it
        call: Call = Call.objects.get(pk=self.context["view"].kwargs["call_pk"])
        validated_data["call"] = call
        return super().create(validated_data)

    class Meta:
        model = CallSentiment
        fields = (
            "id",
            "overall_sentiment_score",
            "caller_sentiment_score",
            "callee_sentiment_score",
            "raw_call_sentiment_model_run_id",
            "call_sentiment_model_run",
        )
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
