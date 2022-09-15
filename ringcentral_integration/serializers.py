import logging
from typing import Dict

from rest_framework import serializers

from .models import (
    RingCentralSessionEvent
)

log = logging.getLogger(__name__)

class RingCentralSessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RingCentralSessionEvent
        # read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = "__all__"
    
    def create(self, validated_data: Dict):
        print(validated_data)
        instance = super().create(validated_data)

        return instance