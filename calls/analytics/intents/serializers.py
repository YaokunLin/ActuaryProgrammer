from rest_framework import serializers

from calls.analytics.intents.models import (
    CallMentionedCompany,
    CallMentionedInsurance,
    CallOutcome,
    CallOutcomeReason,
    CallMentionedProcedure,
    CallMentionedProduct,
    CallPurpose,
    CallMentionedSymptom,
)


class CallPurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallPurpose
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallOutcome
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallOutcomeReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallOutcomeReason
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedCompany
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedInsuranceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedInsurance
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedProcedure
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedProduct
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedSymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedSymptom
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
