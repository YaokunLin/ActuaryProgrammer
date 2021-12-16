from rest_framework import serializers

from .models import VeloxExtractData


class VeloxExtractDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeloxExtractData
        # fields = []