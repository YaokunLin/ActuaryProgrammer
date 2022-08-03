from rest_framework import viewsets
from rest_framework.generics import ListAPIView
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
from calls.analytics.intents.serializers import (
    CallMentionedCompanySerializer,
    CallMentionedInsuranceSerializer,
    CallMentionedProcedureKeywordOnlySerializer,
    CallMentionedProductSerializer,
    CallMentionedProcedureSerializer,
    CallMentionedSymptomSerializer,
    CallOutcomeSerializer,
    CallOutcomeReasonSerializer,
    CallPurposeSerializer,
)


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


class CallMentionedCompanyViewset(viewsets.ModelViewSet):
    queryset = CallMentionedCompany.objects.all().order_by("-modified_at")
    serializer_class = CallMentionedCompanySerializer
    filter_fields = ["call__id", "keyword"]


class CallMentionedInsuranceViewset(viewsets.ModelViewSet):
    queryset = CallMentionedInsurance.objects.all().order_by("-modified_at")
    serializer_class = CallMentionedInsuranceSerializer
    filter_fields = ["call__id", "keyword"]


class CallMentionedProcedureViewset(viewsets.ModelViewSet):
    queryset = CallMentionedProcedure.objects.all().order_by("-modified_at")
    serializer_class = CallMentionedProcedureSerializer
    filter_fields = ["call__id", "keyword"]


class CallMentionedProcedureDistinctView(ListAPIView):
    queryset = CallMentionedProcedure.objects.all().distinct("keyword")
    serializer_class = CallMentionedProcedureKeywordOnlySerializer


class CallMentionedProductViewset(viewsets.ModelViewSet):
    queryset = CallMentionedProduct.objects.all().order_by("-modified_at")
    serializer_class = CallMentionedProductSerializer
    filter_fields = ["call__id", "keyword"]


class CallMentionedSymptomViewset(viewsets.ModelViewSet):
    queryset = CallMentionedSymptom.objects.all().order_by("-modified_at")
    serializer_class = CallMentionedSymptomSerializer
    filter_fields = ["call__id", "keyword"]
