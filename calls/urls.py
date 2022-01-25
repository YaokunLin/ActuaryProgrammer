from django.urls import include, path
from rest_framework import routers

from .views import (
    CallAudioPartialViewset,
    CallViewset,
    CallLabelViewset,
    TelecomCallerNameInfoViewSet,
)

router = routers.DefaultRouter()

router.register(r"calls", CallViewset)

call_audio_router = routers.DefaultRouter()
call_audio_router.register(r"partials", CallAudioPartialViewset, basename="call-audio-partials")

router.register(r"labels", CallLabelViewset)

# TODO: I hate this, let's never use underscores in resource names
router.register(r"telecom_caller_name_info", TelecomCallerNameInfoViewSet)

urlpatterns = router.urls

urlpatterns += [
    path("calls/audio/", include(call_audio_router.urls)),
]
