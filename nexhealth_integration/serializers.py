from rest_framework import serializers

from core.models import Organization, Practice


class NexHealthInitializePracticeSerializer(serializers.Serializer):
    appointment_end_time = serializers.DateTimeField(required=False, allow_null=True, default=None)
    appointment_start_time = serializers.DateTimeField(required=False, allow_null=True, default=None)
    is_institution_bound_to_practice = serializers.BooleanField(required=True, allow_null=False)
    nexhealth_institution_id = serializers.IntegerField(required=True)
    nexhealth_location_id = serializers.IntegerField(required=True)
    nexhealth_subdomain = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    peerlogic_organization_id = serializers.PrimaryKeyRelatedField(many=False, allow_empty=False, allow_null=False, queryset=Organization.objects.all())
    peerlogic_practice_id = serializers.PrimaryKeyRelatedField(many=False, allow_empty=False, allow_null=False, queryset=Practice.objects.all())
