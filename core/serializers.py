from rest_framework import serializers

from .models import Client, Contact


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "group", "rest_base_url"]

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "first_name", "last_name", "placeholder", "mobile_number", "fax_number", "address_line_1", "address_line_2", "zip_code", "zip_code_add_on"]