from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminNetsapiensAPICredentialsViewset,
    netsapiens_call_subscription_event_receiver_view,
    NetsapiensAPICredentialsViewset,
    NetsapiensCdr2ExtractViewset,
    NetsapiensCallSubscriptionsViewset,
)


app_name = "netsapiens_integration"

router = routers.DefaultRouter()
router.register(r"admin/api-credentials", AdminNetsapiensAPICredentialsViewset)
router.register(r"api-credentials", NetsapiensAPICredentialsViewset)
router.register(r"call-subscriptions", NetsapiensCallSubscriptionsViewset, basename="call-subscriptions")
router.register(r"cdr2-extracts", NetsapiensCdr2ExtractViewset, basename="cdr2-extracts")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<practice_telecom_id>/<call_subscription_id>/call-subscription-receiver/",
        netsapiens_call_subscription_event_receiver_view,
        name="call-subscription-event-receiver",
    ),  # if we ever change this name, we must change NetsapiensCallSubscriptions#get_subscription_url
    # path('call-origid-subscription/', netsapiens_call_origid_subscription_event_receiver_view),
]
