from django.shortcuts import render
from rest_framework import viewsets

from .models import Client
from .serializers import ClientSerializer


class ClientViewset(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = Client.objects.all()
        domain = self.request.query_params.get("domain", None)
        if domain is not None:
            queryset = queryset.filter(group__name=domain)
        return queryset
