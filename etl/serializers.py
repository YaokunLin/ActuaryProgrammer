from rest_framework import serializers

from .models import VeloxPatientExtract


class VeloxExtractDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeloxPatientExtract
        fields = "__all__"
