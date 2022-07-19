from rest_framework import viewsets, views
from rest_framework.response import Response

from calls.analytics.intents.field_choices import (
    CallOutcomeTypes,
    CallOutcomeReasonTypes,
    CallPurposeTypes,
)
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
from calls.analytics.intents.serializers import (
    CallDiscussedCompanySerializer,
    CallDiscussedInsuranceSerializer,
    CallOutcomeSerializer,
    CallOutcomeReasonSerializer,
    CallDiscussedProductSerializer,
    CallDiscussedProcedureSerializer,
    CallPurposeSerializer,
    CallDiscussedSymptomSerializer,
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


class CallDiscussedCompanyViewset(viewsets.ModelViewSet):
    queryset = CallDiscussedCompany.objects.all().order_by("-modified_at")
    serializer_class = CallDiscussedCompanySerializer
    filter_fields = ["call__id", "keyword"]


class CallDiscussedInsuranceViewset(viewsets.ModelViewSet):
    queryset = CallDiscussedInsurance.objects.all().order_by("-modified_at")
    serializer_class = CallDiscussedInsuranceSerializer
    filter_fields = ["call__id", "keyword"]


class CallDiscussedProcedureViewset(viewsets.ModelViewSet):
    queryset = CallDiscussedProcedure.objects.all().order_by("-modified_at")
    serializer_class = CallDiscussedProcedureSerializer
    filter_fields = ["call__id", "keyword"]


class CallDiscussedProductViewset(viewsets.ModelViewSet):
    queryset = CallDiscussedProduct.objects.all().order_by("-modified_at")
    serializer_class = CallDiscussedProductSerializer
    filter_fields = ["call__id", "keyword"]


class CallDiscussedSymptomViewset(viewsets.ModelViewSet):
    queryset = CallDiscussedSymptom.objects.all().order_by("-modified_at")
    serializer_class = CallDiscussedSymptomSerializer
    filter_fields = ["call__id", "keyword"]
