from rest_framework import viewsets

from .models import Call, CallLabel
from .serializers import CallSerializer#, CallLabelSerializer

class CallViewset(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    # permission_classes = [permissions.IsAuthenticated]

# class LabelViewset(viewsets.ModelViewSet):
#     queryset = CallLabel.objects.all()
#     serializer_class = CallLabelSerializer