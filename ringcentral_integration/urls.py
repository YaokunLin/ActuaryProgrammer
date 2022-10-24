from django.urls import include, path
from rest_framework import routers

from .views import (  # LoginView,
    AdminRingCentralAPICredentialsViewSet,
    RingCentralCallLegViewSet,
    ringcentral_call_subscription_event_receiver_view,
)

app_name = "ringcentral_integration"

router = routers.DefaultRouter()
router.register(r"admin/api-credentials", AdminRingCentralAPICredentialsViewSet)
router.register(r"call-legs", RingCentralCallLegViewSet, basename="call-legs")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<practice_telecom_id>/<call_subscription_id>/call-subscription-receiver/",
        ringcentral_call_subscription_event_receiver_view,
        name="call-subscription-event-receiver",
    ),
    # path("login", LoginView.as_view()),
]
