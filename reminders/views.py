from django.shortcuts import render
from rest_framework import viewsets

from .models import Cadence
from .serializers import CadenceSerializer


class CadenceViewSet(viewsets.ModelViewSet):
    queryset = Cadence.objects.all().order_by("-created_at")
    serializer_class = CadenceSerializer
