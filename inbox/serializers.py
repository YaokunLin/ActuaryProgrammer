from rest_framework import serializers

from .models import SMSMessage


class SMSMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSMessage
        fields = [
            "id",
            "bandwidth_id",
            "patient",
            "assigned_to_agent",
            "owner",
            "source_number",
            "destination_number",
            "error_code",
            "to_numbers",
            "from_number",
            "text",
            "sent_date_time",
            "delivered_date_time",
            "direction",
            "media",
            "segment_count",
            "priority",
            "expiration",
            "tag",
        ]
        read_only_fields = [
            "id",
            "bandwidth_id",
            "owner",
            "source_number",
            "destination_number",
            "to_numbers",
            "from_number",
            "text",
            "sent_date_time",
            "direction",
            "segment_count",
            "priority",
            "expiration",
            "tag",
        ]