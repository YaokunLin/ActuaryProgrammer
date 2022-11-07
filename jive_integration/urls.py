from django.urls import path
from rest_framework_nested import routers

from jive_integration.views import (
    JiveAWSRecordingBucketViewSet,
    JiveConnectionViewSet,
    webhook,
    cron,
    authentication_callback,
    authentication_connect_url,
    authentication_connect,
)

app_name = "jive_integration"

jive_integration_root_router = routers.SimpleRouter()

jive_integration_root_router.register(r"connections", JiveConnectionViewSet, base_name="jive-connections")

connection_router = routers.NestedSimpleRouter(jive_integration_root_router, r"connections", lookup="connection")

connection_router.register(r"recording-buckets", JiveAWSRecordingBucketViewSet, basename="connection-recording-buckets")

urlpatterns = [
    path("auth/connect-url", authentication_connect_url, name="authentication-connect-url"),
    path("auth/connect", authentication_connect, name="authentication-connect"),
    path("auth/callback", authentication_callback, name="authentication-callback"),
    path("webhook", webhook, name="webhook-receiver"),
    path("cron", cron, name="cron"),
]
