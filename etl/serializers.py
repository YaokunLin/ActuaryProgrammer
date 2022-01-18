from rest_framework import serializers

from .models import NetsapiensCdrsExtract, VeloxPatientExtract


class NetsapiensCdrsExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensCdrsExtract
        fields = "__all__"


class VeloxPatientExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeloxPatientExtract
        fields = "__all__"
