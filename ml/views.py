from rest_framework import viewsets, views
from rest_framework.response import Response

from ml.field_choices import ClassificationDomain
from ml.models import MLModel, MLModelResultHistory
from ml.serializers import MLModelResultHistorySerializer, MLModelSerializer

class MLFieldChoicesView(views.APIView):

    def get(self, request, format=None):
        result = {}
        result["classification_domain"] = dict((y, x) for x, y in ClassificationDomain.choices)
        return Response(result)


class MLModelViewset(viewsets.ModelViewSet):
    queryset = MLModel.objects.all().order_by("-modified_at")
    serializer_class = MLModelSerializer
    filter_fields = ["classification_domain", "model_version"]


class MLModelResultHistoryViewset(viewsets.ModelViewSet):
    queryset = MLModelResultHistory.objects.all().order_by("-modified_at")
    serializer_class = MLModelResultHistorySerializer
    filter_fields = ["classification_domain", "call__id", "model__id", "run_id", "label", "score"]
