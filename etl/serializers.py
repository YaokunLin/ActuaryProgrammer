from rest_framework import serializers

from .models import NetsapiensCallExtract, VeloxPatientExtract


class NetsapiensCallExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensCallExtract
        fields = "__all__"


class VeloxPatientExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeloxPatientExtract
        fields = "__all__"
