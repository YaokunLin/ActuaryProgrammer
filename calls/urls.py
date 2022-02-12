from django.urls import include, path
from rest_framework_nested import routers

from .views import (
    CallAudioPartialViewset,
    CallAudioViewset,
    CallLabelViewset,
    CallPartialViewset,
    CallTranscriptPartialViewset,
    CallTranscriptViewset,
    CallViewset,
    GetCallAudioPartial,
    GetCallAudioPartials,
    GetCallTranscriptPartial,
    GetCallTranscriptPartials,
    TelecomCallerNameInfoViewSet,
)

calls_app_root_router = routers.SimpleRouter()

calls_app_root_router.register(r"calls", CallViewset)
calls_app_root_router.register(r"labels", CallLabelViewset)

call_router = routers.NestedSimpleRouter(calls_app_root_router, r"calls", lookup="call")
call_router.register(r"audio", CallAudioViewset, basename="call-audio")
call_router.register(r"partials", CallPartialViewset, basename="call-partials")
call_router.register(r"transcripts", CallTranscriptViewset, basename="call-transcripts")

call_partials_router = routers.NestedSimpleRouter(call_router, r"partials", lookup="call_partial")
call_partials_router.register(r"audio", CallAudioPartialViewset, basename="call-partial-audio")
call_partials_router.register(r"transcripts", CallTranscriptPartialViewset, basename="call-partial-transcripts")


# TODO: I hate this, let's never use underscores in resource names
# dependency is peerlogic-ml-stream-pipeline repo to change as well
calls_app_root_router.register(r"telecom_caller_name_info", TelecomCallerNameInfoViewSet)


urlpatterns = [
    path(r"audio-partials/<pk>/", GetCallAudioPartial.as_view(), name="audio-partial"),
    path(r"audio-partials/", GetCallAudioPartials.as_view(), name="audio-partials"),
    path(r"transcript-partials/<pk>/", GetCallTranscriptPartial.as_view(), name="transcript-partial"),
    path(r"transcript-partials/", GetCallTranscriptPartials.as_view(), name="transcript-partials"),
    path(r"", include(calls_app_root_router.urls)),
    path(r"", include(call_router.urls)),
    path(r"", include(call_partials_router.urls)),
]
