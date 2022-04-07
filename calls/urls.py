from django.urls import include, path
from rest_framework_nested import routers

from calls.analytics.intents.views import (CallAnalyticsFieldChoicesView,
                                           CallOutcomeReasonViewset,
                                           CallOutcomeViewset,
                                           CallProcedureDiscussedViewset,
                                           CallProductDiscussed,
                                           CallPurposeViewset)
from calls.analytics.transcripts.views import (
    CallLongestPauseViewset, CallSentimentViewset,
    CallTranscriptFragmentSentimentViewset, CallTranscriptFragmentViewset)

from .views import (CallAudioPartialViewset, CallAudioViewset, CallFieldChoicesView,
                    CallLabelViewset, CallPartialViewset,
                    CallTranscriptPartialViewset, CallTranscriptViewset,
                    CallViewset, GetCallAudioPartial, GetCallAudioPartials,
                    GetCallTranscriptPartial, GetCallTranscriptPartials,
                    TelecomCallerNameInfoViewSet)

calls_app_root_router = routers.SimpleRouter()

calls_app_root_router.register(r"calls", CallViewset)
calls_app_root_router.register(r"labels", CallLabelViewset)

call_router = routers.NestedSimpleRouter(calls_app_root_router, r"calls", lookup="call")
call_router.register(r"audio", CallAudioViewset, basename="call-audio")
call_router.register(r"partials", CallPartialViewset, basename="call-partials")
call_router.register(r"transcripts", CallTranscriptViewset, basename="call-transcripts")
call_router.register(r"procedures-discussed", CallProcedureDiscussedViewset, basename="call-procedures-discussed")
call_router.register(r"products-discussed", CallProductDiscussed, basename="call-products-discussed")
call_router.register(r"pauses", CallLongestPauseViewset, basename="call-pauses")
call_router.register(r"purposes", CallPurposeViewset, basename="call-purposes")
call_router.register(r"outcomes", CallOutcomeViewset, basename="call-outcomes")
call_router.register(r"outcome-reasons", CallOutcomeReasonViewset, basename="call-outcome-reasons")
call_router.register(r"sentiments", CallSentimentViewset, "call-sentiments")
call_router.register(r"transcript-fragments", CallTranscriptFragmentViewset, basename="call-transcript-fragments")
call_router.register(r"transcript-fragment-sentiments", CallTranscriptFragmentSentimentViewset, basename="call-transcript-fragment-sentiments")


call_partials_router = routers.NestedSimpleRouter(call_router, r"partials", lookup="call_partial")
call_partials_router.register(r"audio", CallAudioPartialViewset, basename="call-partial-audio")
call_partials_router.register(r"transcripts", CallTranscriptPartialViewset, basename="call-partial-transcripts")


calls_app_root_router.register(r"telecom-caller-name-info", TelecomCallerNameInfoViewSet, basename="telecom-caller-name-info")


urlpatterns = [
    path(r"call-analytics-field-choices", CallAnalyticsFieldChoicesView.as_view(), name="call-analytics-field-choices"),
    path(r"call-field-choices", CallFieldChoicesView.as_view(), name="call-field-choices"),
    path(r"audio-partials/<pk>/", GetCallAudioPartial.as_view(), name="audio-partial"),
    path(r"audio-partials/", GetCallAudioPartials.as_view(), name="audio-partials"),
    path(r"transcript-partials/<pk>/", GetCallTranscriptPartial.as_view(), name="transcript-partial"),
    path(r"transcript-partials/", GetCallTranscriptPartials.as_view(), name="transcript-partials"),
    path(r"", include(calls_app_root_router.urls)),
    path(r"", include(call_router.urls)),
    path(r"", include(call_partials_router.urls)),
]
