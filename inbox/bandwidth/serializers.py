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
    text = serializers.CharField(max_length=2048)
    direction = serializers.CharField(max_length=255)
    to_number = ListField(child=PhoneNumberField(), source="to")
    from_number = PhoneNumberField(source="from")
    # TODO: change to UUIDField
    applicationId = serializers.CharField(max_length=255)
    media = ListField(serializers.CharField(max_length=255), allow_null=True)
    tag = serializers.CharField(max_length=255)
    segmentCount = serializers.IntegerField(min_value=1)

    # def to_internal_value


class MessageDeliveredEventSerializer(serializers.Serializer):
    message_status = serializers.CharField(max_length=255, source="type")  # 'type' is a reserved keyword in python
    delivered_date_time = serializers.DateTimeField(source="time")
    description = serializers.CharField(max_length=255)
    destination_number = PhoneNumberField(source="to")
    # add error code to ErroredEventSerializer
    # error_code = serializers.IntegerField(source="errorCode")
    message = MessageSerializer()

    def to_internal_value(self, data):
        print("to_internal_value")
        print(data)
        data["message_status"] = data.pop("type")
        data["delivered_date_time"] = data.pop("time")
        data["destination_number"] = data.pop("to")

        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        print("to_representation")
        print(ret)
        return ret

    def update(self, instance, validated_data):
        instance.delivered_date_time = validated_data.get("delivered_date_time")
        instance.destination_number = validated_data.get("destination_number")
        instance.direction = validated_data.get("direction", instance.direction)
        instance.segment_count = validated_data.get("segment_count", instance.segment_count)
        instance.owner = validated_data.get("owner", instance.owner)
        instance.save()
        return instance


class CreateSMSMessageAndConvertToBandwidthRequestSerializer(serializers.Serializer):
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
    sent_date_time = serializers.DateTimeField(source="time")
    direction = serializers.CharField(max_length=255)
    to_numbers = ListField(child=PhoneNumberField(), source="to")
    from_number = PhoneNumberField(source="from")
    text = serializers.CharField(max_length=2048)
    tag = serializers.CharField(max_length=255)
    segment_count = serializers.IntegerField(source="segmentCount")

    def to_internal_value(self, data):
        data["sent_date_time"] = data.pop("time")
        data["from_number"] = data.pop("from")
        data["to_numbers"] = data.pop("to")
        data["segment_count"] = data.pop("segmentCount")
        del data["applicationId"]

        return data

    def create(self, validated_data):
        return SMSMessage.objects.create(**validated_data)
