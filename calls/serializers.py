from django.contrib.auth.models import Group

from rest_framework import serializers


from .models import Call


class CallSerializer(serializers.ModelSerializer):
    domain = serializers.SlugRelatedField(queryset=Group.objects.all(), slug_field="name")    

    class Meta:
        model = Call
        fields = "__all__"
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]