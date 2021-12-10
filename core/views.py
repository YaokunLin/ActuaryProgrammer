from django.shortcuts import render
from rest_framework import viewsets

from .models import Client, Patient
from .serializers import ClientSerializer, PatientSerializer


class ClientViewset(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = Client.objects.all()
        domain = self.request.query_params.get("domain", None)
        if domain is not None:
            queryset = queryset.filter(group__name=domain)
        return queryset


class PatientViewset(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

    filterset_fields = ["phone_mobile", "phone_home", "phone_work", "phone_fax"]
    search_fields = ["first_name", "last_name"]
