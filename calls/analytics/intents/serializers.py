from rest_framework import serializers

from calls.analytics.intents.models import (
    CallCompanyDiscussed,
    CallInsuranceDiscussed,
    CallOutcome,
    CallOutcomeReason,
    CallProcedureDiscussed,
    CallProductDiscussed,
    CallPurpose,
    CallSymptomDiscussed,
)
from care.serializers import InlineProcedureSerializer


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


class CallCompanyDiscussedSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallCompanyDiscussed
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallInsuranceDiscussedSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallInsuranceDiscussed
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallProcedureDiscussedSerializer(serializers.ModelSerializer):
    procedure = InlineProcedureSerializer(read_only=True)

    class Meta:
        model = CallProcedureDiscussed
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallProductDiscussedSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallProductDiscussed
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class CallSymptomDiscussedSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CallSymptomDiscussed
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]

