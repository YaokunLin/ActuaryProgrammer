from django.shortcuts import render
from rest_framework import viewsets

from .models import Client, Contact
from .serializers import ClientSerializer, ContactSerializer


class ClientViewset(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = Client.objects.all()
        practice_name = self.request.query_params.get("practice_name", None)
        if practice_name is not None:
            queryset = queryset.filter(practice__name=practice_name)
        return queryset


class ContactViewset(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

    filterset_fields = ["mobile_number"]
    search_fields = ["first_name", "last_name"]
