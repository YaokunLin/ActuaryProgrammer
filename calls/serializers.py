import logging
from typing import Optional

from django.db.models import Prefetch, QuerySet
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from calls.analytics.intents.models import (
    CallMentionedCompany,
    CallMentionedInsurance,
    CallMentionedProcedure,
    CallMentionedProduct,
    CallMentionedSymptom,
    CallPurpose,
)
from calls.analytics.participants.models import AgentEngagedWith
from calls.analytics.participants.serializers import AgentAssignedCallSerializer
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
from calls.models import (
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

# Get an instance of a logger
log = logging.getLogger(__name__)


class CallSerializer(serializers.ModelSerializer):
    engaged_in_calls = serializers.SerializerMethodField(read_only=True)

    # TODO: this should not be many-many definitionally but only works when that is set to True
    assigned_agent = AgentAssignedCallSerializer(many=True, required=False)

    call_purposes = serializers.SerializerMethodField()  # Includes outcome and outcome reasons

    # mentioned, inline
    mentioned_companies = serializers.SerializerMethodField()
    mentioned_insurances = serializers.SerializerMethodField()
    mentioned_procedures = serializers.SerializerMethodField()
    mentioned_products = serializers.SerializerMethodField()
    mentioned_symptoms = serializers.SerializerMethodField()

    # latest audio and transcript URLs
    has_audio = serializers.SerializerMethodField()
    has_transcript = serializers.SerializerMethodField()

    call_sentiments = InlineCallSentimentSerializer(many=True, read_only=True)

    # TODO: Value calculations
    total_value = serializers.ReadOnlyField()

    domain = serializers.CharField(required=False)  # TODO: deprecate

    @staticmethod
    def apply_queryset_prefetches(calls_qs: QuerySet) -> QuerySet:
        return (
            calls_qs.prefetch_related(
                Prefetch("engaged_in_calls", queryset=AgentEngagedWith.objects.order_by("modified_at"), to_attr="agent_engaged_with_by_modified_at")
            )
            .prefetch_related(
                Prefetch(
                    "call_purposes",
                    queryset=CallPurpose.objects.distinct("call_id", "call_purpose_type").prefetch_related("outcome_results__outcome_reason_results"),
                    to_attr="call_purpose_distinct_purpose_types",
                )
            )
            .prefetch_related("call_sentiments")
            .prefetch_related("assigned_agent")
            .prefetch_related("callaudio_set")
            .prefetch_related("calltranscript_set")
            .prefetch_related(
                Prefetch(
                    "mentioned_companies", queryset=CallMentionedCompany.objects.distinct("call_id", "keyword"), to_attr="mentioned_company_distinct_keywords"
                )
            )
            .prefetch_related(
                Prefetch(
                    "mentioned_products", queryset=CallMentionedProduct.objects.distinct("call_id", "keyword"), to_attr="mentioned_product_distinct_keywords"
                )
            )
            .prefetch_related(
                Prefetch(
                    "mentioned_procedures",
                    queryset=CallMentionedProcedure.objects.distinct("call_id", "keyword"),
                    to_attr="mentioned_procedure_distinct_keywords",
                )
            )
            .prefetch_related(
                Prefetch(
                    "mentioned_insurances",
                    queryset=CallMentionedInsurance.objects.distinct("call_id", "keyword"),
                    to_attr="mentioned_insurance_distinct_keywords",
                )
            )
            .prefetch_related(
                Prefetch(
                    "mentioned_symptoms", queryset=CallMentionedSymptom.objects.distinct("call_id", "keyword"), to_attr="mentioned_symptom_distinct_keywords"
                )
            )
        )

    def get_engaged_in_calls(self, call: Call):
        engaged_in_call = []
        if hasattr(call, "agent_engaged_with_by_modified_at"):
            data = call.agent_engaged_with_by_modified_at
            if data:
                engaged_in_call = [data[0]]
        else:
            engaged_in_call = [call.engaged_in_calls.order_by("modified_at").first()]  # using modified-at in the case where we're by-hand tweaking the rdbms

        # TODO: this is a list for contract reasons, make this a single and verify that analytics dashboard doesn't break
        return InlineAgentEngagedWithSerializer(engaged_in_call, many=True).data

    def get_call_purposes(self, call: Call) -> ReturnDict:
        data = getattr(call, "call_purpose_distinct_purpose_types", call.call_purposes.distinct("call_purpose_type"))
        return InlineCallPurposeSerializer(data, many=True).data

    def get_mentioned_companies(self, call: Call) -> ReturnDict:
        data = getattr(call, "mentioned_company_distinct_keywords", call.mentioned_companies.distinct("keyword"))
        return InlineCallMentionedCompanySerializer(data, many=True).data

    def get_mentioned_insurances(self, call: Call) -> ReturnDict:
        data = getattr(call, "mentioned_insurance_distinct_keywords", call.mentioned_insurances.distinct("keyword"))
        return InlineCallMentionedInsuranceSerializer(data, many=True).data

    def get_mentioned_procedures(self, call: Call) -> ReturnDict:
        data = getattr(call, "mentioned_procedure_distinct_keywords", call.mentioned_procedures.distinct("keyword"))
        return InlineCallMentionedProcedureSerializer(data, many=True).data

    def get_mentioned_products(self, call: Call) -> ReturnDict:
        data = getattr(call, "mentioned_product_distinct_keywords", call.mentioned_products.distinct("keyword"))
        return InlineCallMentionedProductSerializer(data, many=True).data

    def get_mentioned_symptoms(self, call: Call) -> ReturnDict:
        data = getattr(call, "mentioned_symptom_distinct_keywords", call.mentioned_symptoms.distinct("keyword"))
        return InlineCallMentionedSymptomSerializer(data, many=True).data

    def get_has_audio(self, call: Call) -> bool:
        return call.callaudio_set.exists()

    def get_has_transcript(self, call: Call) -> bool:
        return call.calltranscript_set.exists()

    class Meta:
        model = Call
        fields = "__all__"
        # TODO: Return non-signed URLs
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "domain", "latest_audio_signed_url", "latest_transcript_signed_url"]


class CallDetailsSerializer(CallSerializer):
    latest_audio_signed_url = serializers.SerializerMethodField()
    latest_transcript_signed_url = serializers.SerializerMethodField()

    def get_latest_audio_signed_url(self, call: Call) -> Optional[str]:
        return call.latest_audio_signed_url

    def get_latest_transcript_signed_url(self, call: Call) -> Optional[str]:
        return call.latest_transcript_signed_url


class CallNestedRouterBaseWriteSerializerMixin(serializers.ModelSerializer):
    def create(self, validated_data):
        call = Call.objects.get(pk=self.context["view"].kwargs["call_pk"])
        validated_data["call"] = call
        return self.Meta.model.objects.create(**validated_data)


class CallNoteReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallNote
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallNoteWriteSerializer(CallNestedRouterBaseWriteSerializerMixin):
    class Meta:
        model = CallNote
        fields = ["note"]
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallTranscriptSerializer(serializers.ModelSerializer):
    signed_url = serializers.CharField(required=False)

    class Meta:
        model = CallTranscript
        fields = [
            "id",
            "call",
            "publish_event_on_patch",
            "mime_type",
            "transcript_type",
            "transcript_text",
            "speech_to_text_model_type",
            "raw_call_transcript_model_run_id",
            "call_transcript_model_run",
            "created_by",
            "created_at",
            "modified_by",
            "modified_at",
            "signed_url",
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
