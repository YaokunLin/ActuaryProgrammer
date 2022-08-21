from rest_framework import serializers

from calls.serializers import CallNestedRouterBaseWriteSerializerMixin
from calls.analytics.intents.models import (
    CallMentionedCompany,
    CallMentionedInsurance,
    CallMentionedProcedure,
    CallMentionedProduct,
    CallMentionedSymptom,
    CallOutcome,
    CallOutcomeReason,
    CallPurpose,
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


#
# Mentioned
#

class CallMentionedCompanyReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallMentionedCompany
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedCompanyWriteSerializer(CallNestedRouterBaseWriteSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = CallMentionedCompany
        fields = ("id", "keyword")
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedInsuranceReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallMentionedInsurance
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedInsuranceWriteSerializer(CallNestedRouterBaseWriteSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = CallMentionedInsurance
        fields = ("id", "keyword")
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedProcedureReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallMentionedProcedure
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedProcedureWriteSerializer(CallNestedRouterBaseWriteSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = CallMentionedProcedure
        fields = ("id", "keyword")
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedProcedureKeywordOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMentionedProcedure
        fields = ["keyword"]
        read_only_fields = ["keyword"]


class CallMentionedProductReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallMentionedProduct
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedProductWriteSerializer(CallNestedRouterBaseWriteSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = CallMentionedProduct
        fields = ("id", "keyword")
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedSymptomReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallMentionedSymptom
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallMentionedSymptomWriteSerializer(CallNestedRouterBaseWriteSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = CallMentionedSymptom
        fields = ("id", "keyword")
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
