from django.urls import include, path
from rest_framework_nested import routers

from calls.analytics.benchmarks.views import (
    CallCountsBenchmarksView,
    OpportunitiesBenchmarksView,
)
from calls.analytics.insurance_providers.views import (
    InsuranceProviderCallMetricsView,
    InsuranceProviderInteractionsView,
)
from calls.analytics.intents.views import (
    CallMentionedCompanyViewset,
    CallMentionedInsuranceViewset,
    CallMentionedProcedureDistinctView,
    CallMentionedProcedureViewset,
    CallMentionedProductViewset,
    CallMentionedSymptomViewset,
    CallOutcomeReasonViewset,
    CallOutcomeViewset,
    CallPurposeViewset,
)
from calls.analytics.interactions.views import (
    AgentCallScoreMetricViewset,
    AgentCallScoreViewset,
)
from calls.analytics.opportunities.views import (
    CallCountsView,
    NewPatientOpportunitiesView,
    NewPatientWinbacksView,
    OpportunitiesPerUserView,
    OpportunitiesView,
)
from calls.analytics.participants.views import (
    AgentAssignedCallViewSet,
    AgentEngagedWithViewset,
)
from calls.analytics.top_mentions.views import (
    TopCompaniesMentionedView,
    TopInsurancesMentionedView,
    TopProceduresMentionedView,
    TopProductsMentionedView,
    TopSymptomsMentionedView,
)
from calls.analytics.transcripts.views import (
    CallLongestPauseViewset,
    CallSentimentViewset,
    CallTranscriptFragmentSentimentViewset,
    CallTranscriptFragmentViewset,
)
from calls.analytics.views import CallAnalyticsFieldChoicesView
from calls.views import (
    CallAudioPartialViewset,
    CallAudioViewset,
    CallFieldChoicesView,
    CallLabelViewset,
    CallNoteViewSet,
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
calls_app_root_router.register(r"agent-call-score-metrics", AgentCallScoreMetricViewset)
calls_app_root_router.register(r"agent-assigned-call", AgentAssignedCallViewSet, basename="agent-assigned-call")

call_router = routers.NestedSimpleRouter(calls_app_root_router, r"calls", lookup="call")
call_router.register(r"audio", CallAudioViewset, basename="call-audio")
call_router.register(r"partials", CallPartialViewset, basename="call-partials")
call_router.register(r"transcripts", CallTranscriptViewset, basename="call-transcripts")
call_router.register(r"agent-call-scores", AgentCallScoreViewset, basename="agent-call-scores")
call_router.register(r"agent-engaged-with", AgentEngagedWithViewset, basename="call-agent-engaged-with")
call_router.register(r"call-notes", CallNoteViewSet, basename="call-notes")
call_router.register(r"mentioned-companies", CallMentionedCompanyViewset, basename="call-mentioned-companies")
call_router.register(r"mentioned-insurances", CallMentionedInsuranceViewset, basename="call-mentioned-insurances")
call_router.register(r"mentioned-procedures", CallMentionedProcedureViewset, basename="call-mentioned-procedures")
call_router.register(r"mentioned-products", CallMentionedProductViewset, basename="call-mentioned-products")
call_router.register(r"mentioned-symptoms", CallMentionedSymptomViewset, basename="call-mentioned-symptoms")
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
    # Field choices
    path(r"call-analytics-field-choices", CallAnalyticsFieldChoicesView.as_view(), name="call-analytics-field-choices"),
    path(r"call-field-choices", CallFieldChoicesView.as_view(), name="call-field-choices"),
    # Call Audio Partials (root)
    path(r"audio-partials/<pk>/", GetCallAudioPartial.as_view(), name="audio-partial"),
    path(r"audio-partials/", GetCallAudioPartials.as_view(), name="audio-partials"),
    # Call Transcript Partials (root)
    path(r"transcript-partials/<pk>/", GetCallTranscriptPartial.as_view(), name="transcript-partial"),
    path(r"transcript-partials/", GetCallTranscriptPartials.as_view(), name="transcript-partials"),
    # Distinct views
    path(r"mentioned-procedures/", CallMentionedProcedureDistinctView.as_view(), name="mentioned-procedures"),
    # Call Aggregates
    path(r"calls/aggregates/insurance-provider-interactions/", InsuranceProviderInteractionsView.as_view(), name="insurance-provider-interactions"),
    path(r"calls/aggregates/new-patient-opportunities/", NewPatientOpportunitiesView.as_view(), name="new-patient-opportunities"),
    path(r"calls/aggregates/new-patient-winback-opportunities/", NewPatientWinbacksView.as_view(), name="new-patient-winback-opportunities"),
    path(r"calls/aggregates/call-counts/", CallCountsView.as_view(), name="call-counts"),
    path(r"calls/aggregates/opportunity-values/", OpportunitiesView.as_view(), name="opportunity-values"),
    path(r"calls/aggregates/outbound-call-counts/", CallCountsView.as_view(), name="outbound-call-counts"),
    path(r"calls/aggregates/opportunities-per-user/", OpportunitiesPerUserView.as_view(), name="opportunities-per-user"),
    path(
        r"calls/aggregates/outbound-insurance-provider-call-counts/", InsuranceProviderCallMetricsView.as_view(), name="outbound-insurance-provider-call-counts"
    ),
    # Top Call Mentions
    path(r"calls/top-mentions/companies/", TopCompaniesMentionedView.as_view(), name="top-mentioned-companies"),
    path(r"calls/top-mentions/insurances/", TopInsurancesMentionedView.as_view(), name="top-mentioned-insurances"),
    path(r"calls/top-mentions/procedures/", TopProceduresMentionedView.as_view(), name="top-mentioned-procedures"),
    path(r"calls/top-mentions/products/", TopProductsMentionedView.as_view(), name="top-mentioned-products"),
    path(r"calls/top-mentions/symptoms/", TopSymptomsMentionedView.as_view(), name="top-mentioned-symptoms"),
    # Benchmarks
    path(r"calls/benchmarks/opportunities/", OpportunitiesBenchmarksView.as_view(), name="opportunities-benchmarks"),
    path(r"calls/benchmarks/call-counts/", CallCountsBenchmarksView.as_view(), name="call-counts-benchmarks"),
    # Routers
    path(r"", include(calls_app_root_router.urls)),
    path(r"", include(call_router.urls)),
    path(r"", include(call_partials_router.urls)),
]
