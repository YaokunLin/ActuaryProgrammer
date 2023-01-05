from concurrent import futures
from datetime import datetime, timedelta

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from core.pubsub_helpers import publish_event
from nexhealth_integration.serializers import (
    NexHealthInitializePracticeSerializer,
    NexHealthSyncPracticeSerializer,
)
from peerlogic.settings import (
    PUBSUB_TOPIC_PATH_NEXHEALTH_INGEST_PRACTICE,
    PUBSUB_TOPIC_PATH_NEXHEALTH_SYNC_PRACTICE,
)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def ingest_practice(request: Request) -> Response:
    serializer = NexHealthInitializePracticeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    now = datetime.utcnow()
    event_data = {
        "appointment_created_at_to": (serializer.validated_data.get("appointment_created_at_to") or (now + timedelta(weeks=52))).isoformat(),
        "appointment_created_at_from": (serializer.validated_data.get("appointment_created_at_from") or (now - timedelta(weeks=52))).isoformat(),
        "is_institution_bound_to_practice": serializer.validated_data["is_institution_bound_to_practice"],
        "nexhealth_institution_id": serializer.validated_data["nexhealth_institution_id"],
        "nexhealth_location_id": serializer.validated_data["nexhealth_location_id"],
        "nexhealth_subdomain": serializer.validated_data["nexhealth_subdomain"],
        "peerlogic_organization_id": serializer.validated_data["peerlogic_organization_id"],
        "peerlogic_practice_id": serializer.validated_data["peerlogic_practice_id"],
    }
    event_attributes = {}
    future = publish_event(event_attributes=event_attributes, event=event_data, topic_path=PUBSUB_TOPIC_PATH_NEXHEALTH_INGEST_PRACTICE)
    futures.wait([future])
    return Response({}, status=HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def sync_practice(request: Request) -> Response:
    serializer = NexHealthSyncPracticeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    event_data = {
        "peerlogic_practice_id": serializer.validated_data["peerlogic_practice_id"],
    }
    event_attributes = {}
    future = publish_event(event_attributes=event_attributes, event=event_data, topic_path=PUBSUB_TOPIC_PATH_NEXHEALTH_SYNC_PRACTICE)
    futures.wait([future])
    return Response({}, status=HTTP_200_OK)
