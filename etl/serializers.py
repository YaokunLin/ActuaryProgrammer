from rest_framework import serializers

from .models import VeloxPatientExtract


class VeloxPatientExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeloxPatientExtract
        fields = "__all__"
