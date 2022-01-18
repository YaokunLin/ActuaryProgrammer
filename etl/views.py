from django.shortcuts import render

from rest_framework import viewsets

from .models import NetsapiensCallExtract, VeloxPatientExtract
from .serializers import NetsapiensCallExtractSerializer, VeloxPatientExtractSerializer


class NetsapiensCallExtractViewset(viewsets.ModelViewSet):
    queryset = NetsapiensCallExtract.objects.all()
    serializer_class = NetsapiensCallExtractSerializer

    filterset_fields = ["peerlogic_call_id", "netsapiens_callid"]


class VeloxPatientExtractViewset(viewsets.ModelViewSet):
    queryset = VeloxPatientExtract.objects.all()
    serializer_class = VeloxPatientExtractSerializer

    filterset_fields = ["peerlogic_patient_id", "velox_id"]
