from django.urls import include, path
from rest_framework import routers

from .views import (
    ringcentral_call_subscription_event_receiver_view,
    # LoginView,
    AdminRingCentralAPICredentialsViewset,
    RingCentralCallLegViewset
)


app_name = "ringcentral_integration"

router = routers.DefaultRouter()
router.register(r"admin/api-credentials", AdminRingCentralAPICredentialsViewset)
router.register(r"call_legs", RingCentralCallLegViewset, basename="call-legs")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<practice_telecom_id>/<call_subscription_id>/call-subscription-receiver/",
        ringcentral_call_subscription_event_receiver_view,
        name="call-subscription-event-receiver",
    ),
    # path("login", LoginView.as_view()),
]
