from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from care.models import Procedure
from core.models import Practice


class ProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]


class ExistingPatientsSerializer(serializers.Serializer):
    appointment_created_before = serializers.DateTimeField(required=True, allow_null=False)
    practice = serializers.PrimaryKeyRelatedField(required=True, many=False, allow_empty=False, allow_null=False, queryset=Practice.objects.all())
    phone_number = PhoneNumberField(required=True, allow_null=False, allow_blank=False)
    name_last = serializers.CharField(required=False, allow_blank=True, max_length=255)
