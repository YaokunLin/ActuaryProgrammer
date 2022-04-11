from rest_framework import serializers

from calls.analytics.intents.models import (
    CallDiscussedCompany,
    CallDiscussedInsurance,
    CallOutcome,
    CallOutcomeReason,
    CallDiscussedProcedure,
    CallDiscussedProduct,
    CallPurpose,
    CallDiscussedSymptom,
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


class CallDiscussedCompanySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallDiscussedCompany
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallDiscussedInsuranceSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallDiscussedInsurance
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallDiscussedProcedureSerializer(serializers.ModelSerializer):

    class Meta:
        model = CallDiscussedProcedure
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallDiscussedProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallDiscussedProduct
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallDiscussedSymptomSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallDiscussedSymptom
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]

