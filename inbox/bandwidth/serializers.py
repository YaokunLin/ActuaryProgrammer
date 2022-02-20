from typing import Dict
from django.conf import settings
from django.db.models.fields import CharField, DateTimeField
from django.http.request import RawPostDataException
from rest_framework import serializers
from drf_compound_fields.fields import ListField

from phonenumber_field.serializerfields import PhoneNumberField
from inbox.field_choices import MESSAGE_STATUSES_DELIVERED

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
    media = ListField(child=serializers.CharField(max_length=255), allow_null=True)
    tag = serializers.CharField(max_length=255)
    segmentCount = serializers.IntegerField(min_value=1)


class MessageDeliveredEventSerializer(serializers.Serializer):
    """https://dev.bandwidth.com/docs/messaging/webhooks/#message-delivered"""

    message_status = serializers.CharField(max_length=255)
    delivered_date_time = serializers.DateTimeField()
    description = serializers.CharField(max_length=255)
    destination_number = PhoneNumberField(source="to")
    source_number = PhoneNumberField(
        source="to",
        required=False,
    )
    # add error code to ErroredEventSerializer
    # error_code = serializers.IntegerField(source="errorCode")
    message = MessageSerializer()

    # Takes the unvalidated incoming data as input and
    # should return the validated data that will be
    # made available as serializer.validated_data
    # internal value runs first
    def to_internal_value(self, data):
        # TODO: put in the bandwidth description in the datamodel
        data.pop("description")
        data["message_status"] = data.pop("type")
        data["delivered_date_time"] = data.pop("time")
        data["destination_number"] = data.pop("to")

        return data

    # To Bandwidth representation, example below:
    # {
    #   'applicationId': 'c1d4708e-78d1-46fc-9b75-7770b4545a15',
    #   'direction': 'out',
    #   'from': '+16026757838',
    #   'id': '16418405240215zg3xeivt636ktzw',
    #   'owner': '+16026757838',
    #   'segmentCount': 1,
    #   'tag': 'test message',
    #   'text': 'sms test',
    #   'time': '2022-01-10T18:48:44.021Z',
    #   'to': ['+14806525408']
    # }
    def to_representation(self, instance: SMSMessage) -> Dict:
        representation = {}
        representation["type"] = instance.message_status
        representation["time"] = instance.delivered_date_time
        representation["description"] = "ok"
        representation["message"] = {}
        representation["message"]["id"] = instance.bandwidth_id
        representation["message"]["time"] = representation["time"]
        representation["message"]["to"] = instance.to_numbers
        representation["message"]["from"] = str(instance.from_number)
        representation["message"]["text"] = instance.text
        representation["message"]["applicationId"] = instance.application_id
        representation["message"]["owner"] = str(instance.owner)
        representation["message"]["direction"] = instance.direction
        representation["message"]["segment_count"] = instance.segment_count

        return representation

    def create(self, validated_data):
        message = validated_data.pop("message")
        validated_data["bandwidth_id"] = message.get("id")
        validated_data["owner"] = message.get("owner")
        validated_data["source_number"] = message.get("source_number", "")
        # destimation_number is in outer
        validated_data["to_numbers"] = message.get("to")
        validated_data["from_number"] = message.get("from")
        validated_data["text"] = message.get("text")
        validated_data["message_status"] = MESSAGE_STATUSES_DELIVERED
        # delivered_date_time is in outer json
        validated_data["direction"] = message.get("direction")
        validated_data["media"] = message.get("media")
        validated_data["segment_count"] = message.get("segmentCount")
        # TODO: Migration - sent_date_time nullable
        validated_data["sent_date_time"] = message.get("time")
        return SMSMessage.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.message_status = MESSAGE_STATUSES_DELIVERED
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


class MessageFailedEventSerializer(serializers.Serializer):
    """https://dev.bandwidth.com/docs/messaging/webhooks/#message-failed"""

    message_status = serializers.CharField(max_length=255)
    delivered_date_time = serializers.DateTimeField()
    description = serializers.CharField(max_length=255)
    destination_number = PhoneNumberField(source="to")
    error_code = serializers.IntegerField(source="errorCode")
    message = MessageSerializer()

    # Takes the unvalidated incoming data as input and
    # should return the validated data that will be
    # made available as serializer.validated_data
    # to_internal_value runs first
    def to_internal_value(self, data):
        data["message_status"] = data.pop("type")
        data["errored_date_time"] = data.pop("time")
        data["destination_number"] = data.pop("to")
        data["error_code"] = data.pop("errorCode")
        data["error_message"] = data.pop("description")

        return data

    # To Bandwidth representation, example below:
    # [
    #   {
    #       'description': 'delivery-receipt-expired',
    #       'errorCode': 9902,
    #       'message': {
    #             'applicationId': '93de2206-9669-4e07-948d-329f4b722ee2',
    #             'direction': 'out',
    #             'from': '+16026757838',
    #             'id': '16418405240215zg3xeivt636ktzw',
    #             'owner': '+16026757838',
    #             'segmentCount': 1,
    #             'text': 'error test #4',
    #             'time': '2016-09-14T18:20:16Z',
    #             'to': ['+14806525408']
    #       },
    #       'time': '2016-09-14T18:20:16Z',
    #       'to': '+14806525408',
    #       'type': 'message-failed'
    #   }
    # ]
    def to_representation(self, instance: SMSMessage) -> Dict:
        representation = {}
        representation["type"] = instance.message_status
        representation["time"] = instance.errored_date_time
        representation["error_code"] = instance.errorCode
        representation["description"] = instance.error_message
        representation["message"] = {}
        representation["message"]["id"] = instance.bandwidth_id
        representation["message"]["time"] = representation["time"]
        representation["message"]["to"] = instance.to_numbers
        representation["message"]["from"] = str(instance.from_number)
        representation["message"]["text"] = instance.text
        representation["message"]["applicationId"] = instance.application_id
        representation["message"]["owner"] = str(instance.owner)
        representation["message"]["direction"] = instance.direction
        representation["message"]["segment_count"] = instance.segment_count

        return representation

    def update(self, instance, validated_data):
        instance.message_status = validated_data.get("message_status")
        instance.errored_date_time = validated_data.get("errored_date_time")
        instance.error_code = validated_data.get("error_code")
        instance.error_message = validated_data.get("error_message")
        instance.destination_number = validated_data.get("destination_number")
        instance.direction = validated_data.get("direction", instance.direction)
        instance.segment_count = validated_data.get("segment_count", instance.segment_count)
        instance.owner = validated_data.get("owner", instance.owner)
        instance.save()
        return instance


class BandwidthResponseToSMSMessageSerializer(serializers.Serializer):
    bandwidth_id = CharField(max_length=30)
    owner = PhoneNumberField()
    sent_date_time = serializers.DateTimeField(source="time")
    direction = serializers.CharField(max_length=255)
    to_numbers = ListField(child=PhoneNumberField(), source="to")
    from_number = PhoneNumberField(source="from")
    text = serializers.CharField(max_length=2048)
    tag = serializers.CharField(max_length=255)
    segment_count = serializers.IntegerField(source="segmentCount")

    def to_internal_value(self, data):
        data["bandwidth_id"] = data.pop("id")
        data["sent_date_time"] = data.pop("time")
        data["from_number"] = data.pop("from")
        data["to_numbers"] = data.pop("to")
        data["segment_count"] = data.pop("segmentCount")
        del data["applicationId"]

        return data

    def create(self, validated_data):
        return SMSMessage.objects.create(**validated_data)
