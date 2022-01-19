import logging

from rest_framework import viewsets
from rest_framework.decorators import (api_view, authentication_classes,
                                       permission_classes)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import NetsapiensCdrsExtract, VeloxPatientExtract
from .serializers import (NetsapiensCdrsExtractSerializer,
                          VeloxPatientExtractSerializer)

# Get an instance of a logger
log = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def netsapiens_call_subscription_view(request):
    log.info(f"Netsapiens Call subscription: \nHeaders: {request.headers}\nPOST Data {request.data}")
    return Response(request.data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def netsapiens_call_origid_subscription_view(request):
    log.info(f"Netsapiens Call ORIG id subscription: \nHeaders: {request.headers}\nPOST Data {request.data}")
    return Response(request.data)


class NetsapiensCdrsExtractViewset(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    queryset = NetsapiensCdrsExtract.objects.all()
    serializer_class = NetsapiensCdrsExtractSerializer

    filterset_fields = ["peerlogic_call_id", "netsapiens_callid"]


class VeloxPatientExtractViewset(viewsets.ModelViewSet):
    queryset = VeloxPatientExtract.objects.all()
    serializer_class = VeloxPatientExtractSerializer

    filterset_fields = ["peerlogic_patient_id", "velox_id"]
