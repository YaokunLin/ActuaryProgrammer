from django.urls import include, path
from rest_framework_nested import routers

from .views import (
    CallAudioPartialViewset,
    CallPartialViewset,
    CallViewset,
    CallLabelViewset,
    CallTranscriptPartialViewset,
    TelecomCallerNameInfoViewSet,
)

calls_app_root_router = routers.SimpleRouter()

calls_app_root_router.register(r"calls", CallViewset)
calls_app_root_router.register(r"labels", CallLabelViewset)

call_router = routers.NestedSimpleRouter(calls_app_root_router, r"calls", lookup="call")
call_router.register(r"partials", CallPartialViewset, basename="call-partials")

call_partials_router = routers.NestedSimpleRouter(call_router, r"partials", lookup="call_partial")
call_partials_router.register(r"audio", CallAudioPartialViewset, basename="call-partial-audio")
call_partials_router.register(r"transcripts", CallTranscriptPartialViewset, basename="call-partial-transcripts")


# TODO: I hate this, let's never use underscores in resource names
# dependency is peerlogic-ml-stream-pipeline repo to change as well
calls_app_root_router.register(r"telecom_caller_name_info", TelecomCallerNameInfoViewSet)


urlpatterns = [
    path(r"", include(calls_app_root_router.urls)),
    path(r"", include(call_router.urls)),
    path(r"", include(call_partials_router.urls)),
]
