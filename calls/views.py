from rest_framework import viewsets

from .models import (
    Call,
    CallerName,
    CallLabel,
)
from .serializers import (
    CallSerializer,
    CallerNameSerializer,
    CallLabelSerializer,
)


class CallViewset(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer


class CallLabelViewset(viewsets.ModelViewSet):
    queryset = CallLabel.objects.all()
    serializer_class = CallLabelSerializer


class CallerNameViewSet(viewsets.ModelViewSet):
    queryset = CallerName.objects.all()
    serializer_class = CallerNameSerializer

