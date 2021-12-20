from django.shortcuts import render

from rest_framework import viewsets

from .models import VeloxPatientExtract
from .serializers import VeloxExtractDataSerializer


class ETLViewset(viewsets.ModelViewSet):
    queryset = VeloxPatientExtract.objects.all()
    serializer_class = VeloxExtractDataSerializer
    
    filterset_fields = ["velox_id", "peerlogic_patient_id"]
    search_fields = ["peerlogic_patient_id"]