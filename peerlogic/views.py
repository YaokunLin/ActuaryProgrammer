from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    """
    This is a health check endpoint which ensures connectivity to cache and DB for monitoring.
    This should NOT be used by LB/container health checks.
    """
    # Cause a 500 if we can't connect to the database
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")

    # Cause a 500 if we can't connect to our cache
    cache.set("health", "check", 5)

    return Response({}, status=HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def status(request: Request) -> Response:
    """
    This is a status endpoint which returns a 200 if the server is running.
    This checks no other downstream systems. This should be used by LB/container health checks.
    """
    return Response({}, status=HTTP_200_OK)
