from django.shortcuts import render

from rest_framework import viewsets

from .models import VeloxExtractData
from .serializers import VeloxExtractDataSerializer


class ETLViewset(viewsets.ModelViewSet):
    queryset = VeloxExtractData.objects.all()
    serializer_class = VeloxExtractDataSerializer