import logging

from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers

from .models import (
    Call,
    CallAudio,
    CallAudioPartial,
    CallLabel,
    CallNote,
    CallPartial,
    CallTranscript,
    CallTranscriptPartial,
    TelecomCallerNameInfo,
)
from calls.inline_serializers import (
    InlineAgentEngagedWithSerializer,
    InlineCallMentionedCompanySerializer,
    InlineCallMentionedInsuranceSerializer,
    InlineCallMentionedProcedureSerializer,
    InlineCallMentionedProductSerializer,
    InlineCallMentionedSymptomSerializer,
    InlineCallPurposeSerializer,
    InlineCallSentimentSerializer,
)
from calls.analytics.participants.serializers import (
    AgentAssignedCallSerializer,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class CallSerializer(serializers.ModelSerializer):
    # TODO: fix multiple agent_engaged_with with same type value
    engaged_in_calls = InlineAgentEngagedWithSerializer(many=True, read_only=True)

    # TODO: this should not be many-many definitionally but only works when that is set to True
    assigned_agent = AgentAssignedCallSerializer(many=True, required=False)

    # TODO: fix both urls (LISTEN)
    latest_audio_signed_url = serializers.CharField(allow_null=True, required=False)
    latest_transcript_signed_url = serializers.CharField(allow_null=True, required=False)
    # TODO: fix multiple call_purposes with same type value
    call_purposes = InlineCallPurposeSerializer(many=True, read_only=True)
    # Include outcome and outcome reasons

    # mentioned, inline
    mentioned_companies = InlineCallMentionedCompanySerializer(many=True, read_only=True)
    mentioned_insurances = InlineCallMentionedInsuranceSerializer(many=True, read_only=True)
    mentioned_procedures = InlineCallMentionedProcedureSerializer(many=True, read_only=True)
    mentioned_products = InlineCallMentionedProductSerializer(many=True, read_only=True)
    mentioned_symptoms = InlineCallMentionedSymptomSerializer(many=True, read_only=True)

    call_sentiments = InlineCallSentimentSerializer(many=True, read_only=True)

    # TODO: Value calculations
    total_value = serializers.ReadOnlyField()

    domain = serializers.CharField(required=False)  # TODO: deprecate

    class Meta:
        model = Call
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "domain", "latest_audio_signed_url", "latest_transcript_signed_url"]


class CallNoteReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallNote
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallNoteWriteSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        call = Call.objects.get(pk=self.context["view"].kwargs["call_pk"])
        validated_data["call"] = call
        return CallNote.objects.create(**validated_data)

    class Meta:
        model = CallNote
        fields = ["note"]
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallTranscriptSerializer(serializers.ModelSerializer):
    signed_url = serializers.CharField(required=False)
    

    class Meta:
        model = CallTranscript
        fields = [
            "id", "call", "publish_event_on_patch", "mime_type", "transcript_type", "transcript_text", "speech_to_text_model_type",
            "raw_call_transcript_model_run_id", "call_transcript_model_run", "created_by", "created_at", "modified_by", "modified_at",
            "signed_url"
        ]
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
