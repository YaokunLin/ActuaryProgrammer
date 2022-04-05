from rest_framework import viewsets

from calls.analytics.intents.models import CallOutcome, CallOutcomeReason, CallProcedureDiscussed, CallPurpose
from calls.analytics.intents.serializers import CallOutcomeSerializer, CallOutcomeReasonSerializer, CallProcedureDiscussedSerializer, CallPurposeSerializer


class CallPurposeViewset(viewsets.ModelViewSet):
    queryset = CallPurpose.objects.all().order_by("-modified_at")
    serializer_class = CallPurposeSerializer
    filter_fields = ["call_purpose_type", "call__id"]


class CallOutcomeViewset(viewsets.ModelViewSet):
    queryset = CallOutcome.objects.all().order_by("-modified_at")
    serializer_class = CallOutcomeSerializer
    filter_fields = ["call_outcome_type", "call_purpose__id", "call_purpose__call__id"]


class CallOutcomeReasonViewset(viewsets.ModelViewSet):
    queryset = CallOutcomeReason.objects.all().order_by("-modified_at")
    serializer_class = CallOutcomeReasonSerializer
    filter_fields = ["call_outcome_reason_type", "call_outcome__id", "call_outcome__call_purpose__id", "call_outcome__call_purpose__call__id"]


class CallProcedureDiscussedViewset(viewsets.ModelViewSet):
    queryset = CallProcedureDiscussed.objects.all().order_by("-modified_at").select_related("procedure")
    serializer_class = CallProcedureDiscussedSerializer
    filter_fields = ["procedure__id", "call__id"]
