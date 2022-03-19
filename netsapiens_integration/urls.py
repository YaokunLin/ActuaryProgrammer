from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminNetsapiensAPICredentialViewset,
    netsapiens_call_subscription_event_receiver_view,
    NetsapiensAPICredentialViewset,
    NetsapiensCdr2ExtractViewset,
    NetsapiensCallSubscriptionViewset,
)


app_name = "netsapiens_integration"

router = routers.DefaultRouter()
router.register(r"admin/api-credentials", AdminNetsapiensAPICredentialViewset)
router.register(r"api-credentials", NetsapiensAPICredentialViewset)
router.register(r"call-subscriptions", NetsapiensCallSubscriptionViewset, basename="call-subscriptions")
router.register(r"cdr2-extracts", NetsapiensCdr2ExtractViewset, basename="cdr2-extracts")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<practice_telecom_id>/<call_subscription_id>/call-subscription-receiver/",
        netsapiens_call_subscription_event_receiver_view,
        name="call-subscription-event-receiver",
    ),  # if we ever change this name, we must change NetsapiensCallSubscription#get_subscription_url
    # path('call-origid-subscription/', netsapiens_call_origid_subscription_event_receiver_view),
]
