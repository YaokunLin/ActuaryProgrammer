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
    CallMentionedCompanyReadSerializer,
    CallMentionedCompanyWriteSerializer,
    CallMentionedInsuranceReadSerializer,
    CallMentionedInsuranceWriteSerializer,
    CallMentionedProcedureKeywordOnlySerializer,
    CallMentionedProcedureReadSerializer,
    CallMentionedProcedureWriteSerializer,
    CallMentionedProductReadSerializer,
    CallMentionedProductWriteSerializer,
    CallMentionedSymptomReadSerializer,
    CallMentionedSymptomWriteSerializer,
    CallOutcomeReasonSerializer,
    CallOutcomeSerializer,
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

    def get_queryset(self):
        queryset = super().get_queryset().filter(call_purpose__call_id=self.kwargs.get("call_pk"))
        return queryset


class CallOutcomeReasonViewset(viewsets.ModelViewSet):
    queryset = CallOutcomeReason.objects.all().order_by("-modified_at")
    serializer_class = CallOutcomeReasonSerializer
    filter_fields = ["call_outcome_reason_type", "call_outcome__id", "call_outcome__call_purpose__id", "call_outcome__call_purpose__call__id"]


#
# Mentioned Viewsets
#


class CallMentionedCompanyViewset(viewsets.ModelViewSet):
    queryset = CallMentionedCompany.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "keyword"]

    serializer_class_read = CallMentionedCompanyReadSerializer
    serializer_class_write = CallMentionedCompanyWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        queryset = super().get_queryset().filter(call=self.kwargs.get("call_pk"))
        return queryset


class CallMentionedInsuranceViewset(viewsets.ModelViewSet):
    queryset = CallMentionedInsurance.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "keyword"]

    serializer_class_read = CallMentionedInsuranceReadSerializer
    serializer_class_write = CallMentionedInsuranceWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        queryset = super().get_queryset().filter(call=self.kwargs.get("call_pk"))
        return queryset


class CallMentionedProcedureViewset(viewsets.ModelViewSet):
    queryset = CallMentionedProcedure.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "keyword"]

    serializer_class_read = CallMentionedProcedureReadSerializer
    serializer_class_write = CallMentionedProcedureWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        queryset = super().get_queryset().filter(call=self.kwargs.get("call_pk"))
        return queryset


class CallMentionedProcedureDistinctView(ListAPIView):
    queryset = CallMentionedProcedure.objects.all().distinct("keyword")
    serializer_class = CallMentionedProcedureKeywordOnlySerializer


class CallMentionedProductViewset(viewsets.ModelViewSet):
    queryset = CallMentionedProduct.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "keyword"]

    serializer_class_read = CallMentionedProductReadSerializer
    serializer_class_write = CallMentionedProductWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        queryset = super().get_queryset().filter(call=self.kwargs.get("call_pk"))
        return queryset


class CallMentionedSymptomViewset(viewsets.ModelViewSet):
    queryset = CallMentionedSymptom.objects.all().order_by("-modified_at")
    filter_fields = ["call__id", "keyword"]

    serializer_class_read = CallMentionedSymptomReadSerializer
    serializer_class_write = CallMentionedSymptomWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        queryset = super().get_queryset().filter(call=self.kwargs.get("call_pk"))
        return queryset
