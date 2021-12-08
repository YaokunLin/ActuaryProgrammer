from rest_framework import serializers

from .models import Client, Contact


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "group", "rest_base_url"]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = "__all__"
