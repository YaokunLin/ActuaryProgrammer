from django.urls import include, path
from rest_framework_nested import routers

from jive_integration.views import (
    JiveAWSRecordingBucketViewSet,
    JiveConnectionViewSet,
    authentication_callback,
    authentication_connect,
    authentication_connect_url,
    cron,
    webhook,
)

app_name = "jive_integration"

jive_integration_root_router = routers.SimpleRouter()
jive_integration_root_router.register(r"connections", JiveConnectionViewSet, basename="jive-connections")

connection_router = routers.NestedSimpleRouter(jive_integration_root_router, r"connections", lookup="connection")
connection_router.register(r"recording-buckets", JiveAWSRecordingBucketViewSet, basename="connection-recording-buckets")

urlpatterns = [
    path("auth/connect-url", authentication_connect_url, name="authentication-connect-url"),
    path("auth/connect", authentication_connect, name="authentication-connect"),
    path("auth/callback", authentication_callback, name="authentication-callback"),
    path("webhook", webhook, name="webhook-receiver"),
    path("cron", cron, name="cron"),
    # Routers
    path(r"", include(jive_integration_root_router.urls)),
    path(r"", include(connection_router.urls)),
]
