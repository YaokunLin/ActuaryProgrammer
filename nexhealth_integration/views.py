from concurrent import futures
from datetime import datetime, timedelta
from logging import getLogger

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from core.pubsub_helpers import publish_event
from nexhealth_integration.models import Institution
from nexhealth_integration.nexhealth_api_client import NexHealthAPIClient
from nexhealth_integration.serializers import (
    NexHealthIngestPracticeSerializer,
    NexHealthSyncPracticeSerializer,
)
from nexhealth_integration.utils import (
    NexHealthLogAdapter,
    persist_nexhealth_access_token,
)
from peerlogic.settings import (
    NEXHEALTH_API_ROOT_URL,
    PUBSUB_TOPIC_PATH_NEXHEALTH_SYNC_PRACTICE,
)

log = NexHealthLogAdapter(getLogger(__name__))


@api_view(["POST"])
@permission_classes([IsAdminUser])
def ingest_practice(request: Request) -> Response:
    serializer = NexHealthIngestPracticeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    nexhealth_access_token = serializer.validated_data.get("nexhealth_access_token")
    nexhealth_subdomain = serializer.validated_data["nexhealth_subdomain"]
    nexhealth_institution_id = serializer.validated_data["nexhealth_institution_id"]
    nexhealth_location_id = serializer.validated_data["nexhealth_location_id"]
    if nexhealth_access_token:
        log.info(
            "Validating new access token for subdomain=%s, institution_id=%s, location_id=%s",
            nexhealth_subdomain,
            nexhealth_institution_id,
            nexhealth_location_id,
        )
        try:
            nexhealth_client = NexHealthAPIClient(
                NEXHEALTH_API_ROOT_URL, nexhealth_access_token, nexhealth_institution_id, nexhealth_location_id, nexhealth_subdomain
            )
            location_response = nexhealth_client.get_location()
            if location_response.response_status != 200:
                raise Exception(location_response.response_nh_error)
        except Exception:
            log.exception(
                "Error validating new access token for subdomain=%s, institution_id=%s, location_id=%s",
                nexhealth_subdomain,
                nexhealth_institution_id,
                nexhealth_location_id,
            )
            return Response({"errors": [{"nexhealth_access_token": "Error validating provided nexhealth_access_token!"}]}, status=HTTP_400_BAD_REQUEST)

        log.info(
            "New access token validated for subdomain=%s, institution_id=%s, location_id=%s! Storing in secret manager",
            nexhealth_subdomain,
            nexhealth_institution_id,
            nexhealth_location_id,
        )
        persist_nexhealth_access_token(nexhealth_subdomain, nexhealth_access_token)
        log.info(
            "New access token stored in secret manager successfully for subdomain=%s, institution_id=%s, location_id=%s",
            nexhealth_subdomain,
            nexhealth_institution_id,
            nexhealth_location_id,
        )

    institution_exists = Institution.objects.filter(nh_subdomain=nexhealth_subdomain).exists()
    if not institution_exists and not nexhealth_access_token:
        return Response({"errors": [{"nexhealth_access_token": "This field is required for initialization!"}]}, status=HTTP_400_BAD_REQUEST)

    now = datetime.utcnow()
    event_data = {
        "appointment_created_at_to": (serializer.validated_data.get("appointment_created_at_to") or (now + timedelta(weeks=52))).isoformat(),
        "appointment_created_at_from": (serializer.validated_data.get("appointment_created_at_from") or (now - timedelta(weeks=52))).isoformat(),
        "is_institution_bound_to_practice": serializer.validated_data["is_institution_bound_to_practice"],
        "nexhealth_institution_id": nexhealth_institution_id,
        "nexhealth_location_id": nexhealth_location_id,
        "nexhealth_subdomain": nexhealth_subdomain,
        "peerlogic_practice_id": serializer.validated_data["peerlogic_practice_id"],
    }
    event_attributes = {}

    # future = publish_event(event_attributes=event_attributes, event=event_data, topic_path=PUBSUB_TOPIC_PATH_NEXHEALTH_INGEST_PRACTICE)
    # futures.wait([future])
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
