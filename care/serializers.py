from rest_framework import serializers

from care.models import Procedure


class ProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class InlineProcedureSerializer(serializers.Serializer):
    id = serializers.CharField()
    procedure_price_average_in_usd = serializers.DecimalField(max_digits=7, decimal_places=2)
    keyword = serializers.CharField()
    ada_code = serializers.CharField()
