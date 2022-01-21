import logging

from rest_framework import viewsets

from .models import VeloxPatientExtract
from .serializers import VeloxPatientExtractSerializer

# Get an instance of a logger
log = logging.getLogger(__name__)


class VeloxPatientExtractViewset(viewsets.ModelViewSet):
    queryset = VeloxPatientExtract.objects.all()
    serializer_class = VeloxPatientExtractSerializer

    filterset_fields = ["peerlogic_patient_id", "velox_id"]
