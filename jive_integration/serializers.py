import logging
import re
from datetime import datetime
from typing import Dict

from rest_framework import serializers

from core.serializers import UnixEpochDateField
from jive_integration.models import (
    JiveAWSRecordingBucket,
    JiveConnection,
    JiveSubscriptionEventExtract,
)

log = logging.getLogger(__name__)

CAMELCASE_REGEX_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


class JiveConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiveConnection
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "last_sync"]
        fields = ["id", "created_by", "created_at", "modified_by", "modified_at", "practice_telecom", "last_sync", "active"]


class JiveAWSRecordingBucketSerializer(serializers.ModelSerializer):
    class Meta:
        model = JiveAWSRecordingBucket
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "modified_by",
            "modified_at",
            "connection",
            "access_key_id",
            "username",
            "policy_arn",
            "bucket_name",
        ]
        fields = ["id", "connection", "access_key_id", "username", "policy_arn", "bucket_name"]


class JiveSubscriptionEventExtractSerializer(serializers.ModelSerializer):
    data_created = UnixEpochDateField(required=False)

    class Meta:
        model = JiveSubscriptionEventExtract
        read_only_fields = ["id", "created_by", "created_at", "modified_by", "modified_at"]
        fields = "__all__"

    def to_internal_value(self, incoming_data):
        """
        Takes the unvalidated incoming data as input and return the validated data that will be made available as serializer.validated_data internal value runs first

        camelcase to snake_case the rest
        """

        return_value = {}
        return_value.update({"jive_extract": incoming_data})

        for key, value in incoming_data.items():
            model_field_snaked = CAMELCASE_REGEX_PATTERN.sub("_", key).lower()
            if key == "type":  # avoid problems with python type builtin
                return_value.update({"jive_type": value})
            else:
                return_value.update({model_field_snaked: value})

        # TODO: don't mutate or pop from return_value
        jive_data_dictionary = incoming_data.get("data")
        if jive_data_dictionary:
            for key, value in jive_data_dictionary.items():
                model_field_snaked = CAMELCASE_REGEX_PATTERN.sub("_", key).lower()

                model_field_snaked = f"data_{model_field_snaked}"
                return_value.update({model_field_snaked: value})
            # TODO: dry the inner objects up, need to move on
            # callee inner object
            data_callee = return_value.get("data_callee")
            return_value["data_callee_name"] = data_callee.get("name")
            return_value["data_callee_number"] = data_callee.get("number")
            return_value.pop("data_callee")

            # caller inner object
            data_caller = return_value.get("data_caller")
            return_value["data_caller_name"] = data_caller.get("name")
            return_value["data_caller_number"] = data_caller.get("number")
            return_value.pop("data_caller")

            data_recordings_extract = return_value.pop("data_recordings")
            return_value["data_recordings_extract"] = data_recordings_extract
            return_value.pop("data")

        data_created = return_value.get("data_created")
        if type(data_created) != None and type(data_created) != datetime:  # convert to datetime if present
            data_created = datetime.fromtimestamp(int(data_created / 1000))
            return_value.update({"data_created": data_created})

        if not incoming_data.get("peerlogic_call_id"):
            return_value.update({"peerlogic_call_id": ""})  # conform to Django's blankable charfields as opposed to null fields

        return return_value
