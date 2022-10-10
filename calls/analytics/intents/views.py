from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

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
from calls.models import Call


class CallPurposeViewset(viewsets.ModelViewSet):
    queryset = CallPurpose.objects.all().order_by("-modified_at")
    serializer_class = CallPurposeSerializer
    filter_fields = ["call_purpose_type", "call__id"]

    def get_queryset(self):
        queryset = super().get_queryset().filter(call_id=self.kwargs.get("call_pk"))
        return queryset

    def create(self, request, *args, **kwargs):
        # overridden to provide the ability to perform single or multiple object creation
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # get call to update
            call: Call = Call.objects.get(pk=self.kwargs.get("call_pk"))

            # delete existing CallPurpose objects
            call_purposes = call.call_purposes.all()
            if call_purposes:
                call_purposes.delete()

            # create the new / replacement CallPurpose objects
            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CallOutcomeViewset(viewsets.ModelViewSet):
    queryset = CallOutcome.objects.all().order_by("-modified_at")
    serializer_class = CallOutcomeSerializer
    filter_fields = ["call_outcome_type", "call_purpose__id", "call_purpose__call__id"]

    def get_queryset(self):
        # TODO: probably nest outcomes underneath a purpose
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
