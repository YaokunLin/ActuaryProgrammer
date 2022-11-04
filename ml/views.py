from typing import Any

from rest_framework import exceptions, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from ml.field_choices import ClassificationDomain
from ml.models import MLModel, MLModelResultHistory
from ml.serializers import (
    MLModelResultHistoryBulkCreateSerializer,
    MLModelResultHistorySerializer,
    MLModelSerializer,
)


class MLFieldChoicesView(views.APIView):
    def get(self, request, format=None):
        result = {}
        result["classification_domain"] = dict((y, x) for x, y in ClassificationDomain.choices)
        return Response(result)


class MLModelViewset(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)
    queryset = MLModel.objects.all().order_by("-modified_at")
    serializer_class = MLModelSerializer
    filter_fields = ["classification_domain", "model_version"]


class MLModelResultHistoryViewset(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminUser,)
    queryset = MLModelResultHistory.objects.all().order_by("-modified_at")
    serializer_class = MLModelResultHistorySerializer
    filter_fields = ["classification_domain", "call__id", "model__id", "run_id", "label", "score"]
    http_method_names = ["head", "options", "get", "post"]

    @action(detail=False, methods=["post"])
    def bulk(self, request: Request) -> Response:
        serializer = MLModelResultHistoryBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_objects = MLModelResultHistory.objects.bulk_create(
            [MLModelResultHistory(**r) for r in serializer.validated_data["records"]], ignore_conflicts=True
        )

        # Dumbed down serializer here since we don't want to do any unnecessary DB shenanigans
        output_serializer = MLModelResultHistoryBulkCreateSerializer({"records": created_objects})
        return Response(status=HTTP_201_CREATED, data=output_serializer.data)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        raise exceptions.MethodNotAllowed(method=request.method)
