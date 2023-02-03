from rest_framework import serializers

from core.models import Practice


class NexHealthIngestPracticeSerializer(serializers.Serializer):
    appointment_created_at_from = serializers.DateTimeField(required=False, allow_null=True, default=None)
    appointment_created_at_to = serializers.DateTimeField(required=False, allow_null=True, default=None)
    is_institution_bound_to_practice = serializers.BooleanField(required=True, allow_null=False)
    nexhealth_institution_id = serializers.IntegerField(required=True)
    nexhealth_location_id = serializers.IntegerField(required=True)
    nexhealth_subdomain = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    peerlogic_practice_id = serializers.PrimaryKeyRelatedField(required=True, many=False, allow_empty=False, allow_null=False, queryset=Practice.objects.all())

    nexhealth_access_token = serializers.CharField(required=False, allow_null=False, allow_blank=True, default=None)


class NexHealthSyncPracticeSerializer(serializers.Serializer):
    peerlogic_practice_id = serializers.PrimaryKeyRelatedField(required=True, many=False, allow_empty=False, allow_null=False, queryset=Practice.objects.all())
