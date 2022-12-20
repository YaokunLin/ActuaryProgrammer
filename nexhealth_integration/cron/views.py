import logging
from concurrent import futures
from datetime import datetime, timedelta

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from core.pubsub_helpers import publish_event
from nexhealth_integration.models import Location
from nexhealth_integration.utils import NexHealthLogAdapter
from peerlogic.settings import PUBSUB_TOPIC_PATH_NEXHEALTH_INGEST_PRACTICE

log = NexHealthLogAdapter(logging.getLogger(__name__))


@api_view(["GET"])
@permission_classes([AllowAny])  # We have other "auth" checks below. Read on.
@authentication_classes([])
def update_practices(request: Request) -> Response:
    """
    This endpoint is hit on a "cron" schedule by GCP.

    In remote deployments, this path will not be publicly accessible.
    We also check for the presence of a header:

    More info: https://cloud.google.com/appengine/docs/flexible/scheduling-jobs-with-cron-yaml
    """

    # GCP strips this header from external requests, so it's a safe check
    if not request.META.get("HTTP_X_APPENGINE_CRON") == "true":  # X-Appengine-Cron
        log.warning("Rejecting request to cron endpoint with missing/incorrect 'X-Appengine-Cron' header!")
        raise NotFound()

    locations = (
        Location.objects.select_related("peerlogic_practice", "nh_institution__peerlogic_practice")
        .filter(
            is_initialized=True,
            peerlogic_practice__active=True,
        )
        .all()
    )

    now = datetime.utcnow()
    gcp_futures = []
    for location in locations:
        event_data = {
            "appointment_end_time": (now + timedelta(weeks=52)).isoformat(),
            "appointment_start_time": (now - timedelta(weeks=52)).isoformat(),
            "is_institution_bound_to_practice": location.nh_institution.peerlogic_practice == location.peerlogic_practice,
            "nexhealth_institution_id": location.nh_institution_id,
            "nexhealth_location_id": location.nh_id,
            "nexhealth_subdomain": location.nh_institution.nh_subdomain,
            "peerlogic_organization_id": location.peerlogic_practice.organization_id,
            "peerlogic_practice_id": location.peerlogic_practice.id,
        }
        gcp_futures.append(publish_event(event_attributes={}, event=event_data, topic_path=PUBSUB_TOPIC_PATH_NEXHEALTH_INGEST_PRACTICE))
    if futures:
        futures.wait(gcp_futures)
    return Response({}, status=HTTP_200_OK)
