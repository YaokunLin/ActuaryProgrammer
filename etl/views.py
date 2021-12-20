from django.shortcuts import render

from rest_framework import viewsets

from .models import VeloxPatientExtract
from .serializers import VeloxPatientExtractSerializer


class ETLViewset(viewsets.ModelViewSet):
    queryset = VeloxPatientExtract.objects.all()
    serializer_class = VeloxPatientExtractSerializer

    filterset_fields = ["peerlogic_patient_id", "velox_id"]
