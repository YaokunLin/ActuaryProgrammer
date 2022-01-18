from django.shortcuts import render

from rest_framework import viewsets

from .models import NetsapiensCdrsExtract, VeloxPatientExtract
from .serializers import NetsapiensCdrsExtractSerializer, VeloxPatientExtractSerializer


class NetsapiensCdrsExtractViewset(viewsets.ModelViewSet):
    queryset = NetsapiensCdrsExtract.objects.all()
    serializer_class = NetsapiensCdrsExtractSerializer

    filterset_fields = ["peerlogic_call_id", "netsapiens_callid"]


class VeloxPatientExtractViewset(viewsets.ModelViewSet):
    queryset = VeloxPatientExtract.objects.all()
    serializer_class = VeloxPatientExtractSerializer

    filterset_fields = ["peerlogic_patient_id", "velox_id"]
