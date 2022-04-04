from rest_framework import viewsets

from care.models import Procedure
from care.serializers import ProcedureSerializer


class ProcedureViewset(viewsets.ModelViewSet):
    queryset = Procedure.objects.all().order_by("-modified_at")
    serializer_class = ProcedureSerializer
    filter_fields = ["ada_code", "procedure_price_average"]
