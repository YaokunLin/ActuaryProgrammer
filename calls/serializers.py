from rest_framework import serializers

from core.models import GroupTelecom

from .models import Call


class CallSerializer(serializers.ModelSerializer):
    domain = serializers.PrimaryKeyRelatedField(queryset=GroupTelecom.objects.all())    

    class Meta:
        model = Call
        fields = "__all__"
        read_only_fields = ["id"]