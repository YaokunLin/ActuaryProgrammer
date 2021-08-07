from rest_framework import serializers

from .models import Cadence


class CadenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cadence
        fields = ["id", "client", "user_sending_reminder", "cadence_type"]
