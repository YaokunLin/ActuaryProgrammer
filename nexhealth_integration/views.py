from concurrent import futures

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from core.pubsub_helpers import publish_event
from peerlogic.settings import PUBSUB_TOPIC_PATH_NEXHEALTH_FOO


@api_view(["POST"])
@permission_classes([IsAdminUser])
def foo(request: Request) -> Response:
    event_data = {}
    event_attributes = {}
    future = publish_event(event_attributes=event_attributes, event=event_data, topic_path=PUBSUB_TOPIC_PATH_NEXHEALTH_FOO)
    futures.wait([future])
    return Response({}, status=HTTP_200_OK)
