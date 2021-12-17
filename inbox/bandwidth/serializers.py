from django.conf import settings
from django.db.models.fields import CharField, DateTimeField
from django.http.request import RawPostDataException
from rest_framework import serializers
from drf_compound_fields.fields import ListField

from phonenumber_field.serializerfields import PhoneNumberField

from inbox.models import SMSMessage


class MessageSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255)
    owner = PhoneNumberField()
    time = serializers.DateTimeField()
    direction = serializers.CharField(max_length=255)
    to_number = ListField(child=PhoneNumberField(), source="to")
    from_number = PhoneNumberField(source="from")
    applicationId = serializers.CharField(max_length=255)
    media = ListField(child=serializers.CharField(max_length=255), allow_null=True)
    tag = serializers.CharField(max_length=255)
    segmentCount = serializers.IntegerField(min_value=1)


class MessageEventSerializer(serializers.Serializer):
    event_type = serializers.CharField(source=type, max_length=255)  # 'type' is a reserved keyword in python
    time = serializers.DateTimeField()
    description = serializers.CharField(max_length=255)
    to_number = PhoneNumberField(source="to")
    error_code = serializers.IntegerField(source="errorCode")
    message = MessageSerializer()


class CreateMessageSerializer(serializers.Serializer):
    to_numbers = ListField(child=PhoneNumberField())
    from_number = PhoneNumberField()
    text = serializers.CharField(max_length=2048)
    tag = serializers.CharField(max_length=255)

    def to_representation(self, instance):
        """'from' is a reserved keyword, so we adjusted 'to' for consistency"""
        representation = super().to_representation(instance)
        representation["to"] = representation.pop("to_numbers")
        representation["from"] = representation.pop("from_number")

        # always pass applicationId
        representation["applicationId"] = settings.BANDWIDTH_APPLICATION_ID
        return representation


class BandwidthResponseToSMSMessageSerializer(serializers.Serializer):
    id = CharField(max_length=30)
    owner = PhoneNumberField()
    from_date_time = serializers.DateTimeField(source="time")
    direction = serializers.CharField(max_length=255)
    to_numbers = ListField(child=PhoneNumberField(), source="to")
    from_number = PhoneNumberField(source="from")
    text = serializers.CharField(max_length=2048)
    tag = serializers.CharField(max_length=255)
    segment_count = serializers.IntegerField(source="segmentCount")

    def to_internal_value(self, data):
        data["from_date_time"] = data.pop("time")
        data["from_number"] = data.pop("from")
        data["to_numbers"] = data.pop("to")
        data["segment_count"] = data.pop("segmentCount")
        del data["applicationId"]

        return data

    def create(self, validated_data):
        return SMSMessage.objects.create(**validated_data)
