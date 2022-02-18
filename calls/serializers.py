import logging

from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers

from .models import Call, CallAudio, CallAudioPartial, CallLabel, CallPartial, CallTranscript, CallTranscriptPartial, TelecomCallerNameInfo


# Get an instance of a logger
log = logging.getLogger(__name__)


class CallSerializer(serializers.ModelSerializer):
    domain = serializers.CharField(required=False)
    class Meta:
        model = Call
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "domain"]


class CallTranscriptSerializer(serializers.ModelSerializer):
    signed_url = serializers.CharField(required=False)

    class Meta:
        model = CallTranscript
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class CallAudioSerializer(serializers.ModelSerializer):
    signed_url = serializers.CharField(required=False)

    class Meta:
        model = CallAudio
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class InlineCallPartialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallPartial
        fields = ["id", "time_interaction_started", "time_interaction_ended"]
        read_only_fields = ["id", "time_interaction_started", "time_interaction_ended"]


class CallPartialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallPartial
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class CallAudioPartialSerializer(serializers.ModelSerializer):
    signed_url = serializers.CharField(required=False)

    class Meta:
        model = CallAudioPartial
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class CallAudioPartialReadOnlySerializer(serializers.ModelSerializer):
    call_partial = InlineCallPartialSerializer(required=False)
    signed_url = serializers.CharField(required=False)

    class Meta:
        model = CallAudioPartial
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class CallTranscriptPartialReadOnlySerializer(serializers.ModelSerializer):
    call_partial = InlineCallPartialSerializer(required=False)
    signed_url = serializers.CharField(required=False)

    class Meta:
        model = CallTranscriptPartial
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class CallTranscriptPartialSerializer(serializers.ModelSerializer):
    signed_url = serializers.CharField(required=False)

    # Must call after validation step because models are now populated
    def validate_call_partial_relationship(self, call_partial, call_partial_of_audio):
        if call_partial_of_audio and call_partial.id != call_partial_of_audio.id:
            raise serializers.ValidationError({"error": "call_audio_partial's call_partial and this object's call_partial must match. Not saving."})

    def create(self, validated_data):
        if validated_data.get("call_audio_partial"):
            self.validate_call_partial_relationship(validated_data.get("call_partial"), validated_data.get("call_audio_partial").call_partial)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("call_audio_partial"):
            self.validate_call_partial_relationship(validated_data.get("call_partial"), validated_data.get("call_audio_partial").call_partial)
        super().update(instance, validated_data)

    class Meta:
        model = CallTranscriptPartial
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "signed_url"]


class CallLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLabel
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class TelecomCallerNameInfoSerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = TelecomCallerNameInfo
        fields = [
            "phone_number",
            "caller_name",
            "caller_name_type",
            "caller_name_type",
            "country_code",
            "source",
            "carrier_name",
            "carrier_type",
            "mobile_country_code",
            "mobile_network_code",
            "created_at",
            "modified_by",
            "modified_at",
        ]
        read_only_fields = ["created_at", "modified_by", "modified_at"]
