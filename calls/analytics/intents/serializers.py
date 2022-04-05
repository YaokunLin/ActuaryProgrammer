from rest_framework import serializers

from calls.analytics.intents.models import CallOutcome, CallOutcomeReason, CallProcedureDiscussed, CallPurpose
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


class CallProcedureDiscussedSerializer(serializers.ModelSerializer):
    procedure = InlineProcedureSerializer(read_only=True)

    class Meta:
        model = CallProcedureDiscussed
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
