from rest_framework import viewsets

from ml.models import MLModel, MLModelResultHistory
from ml.serializers import MLModelResultHistorySerializer, MLModelSerializer


class MLModelViewset(viewsets.ModelViewSet):
    queryset = MLModel.objects.all().order_by("-modified_at")
    serializer_class = MLModelSerializer
    filter_fields = ["model_type", "model_version"]


class MLModelResultHistoryViewset(viewsets.ModelViewSet):
    queryset = MLModelResultHistory.objects.all().order_by("-modified_at")
    serializer_class = MLModelResultHistorySerializer
    filter_fields = ["call__id", "model__id", "run_id", "label", "score"]
