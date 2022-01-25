from django.urls import include, path
from rest_framework import routers

from .views import (
    AdminNetsapiensAPICredentialsViewset,
    netsapiens_call_subscription_event_receiver_view,
    NetsapiensAPICredentialsViewset,
    NetsapiensCdr2ExtractViewset,
    NetsapiensSubscriptionClientViewset,
)


app_name = "netsapiens_integration"

router = routers.DefaultRouter()
router.register(r"admin/api-credentials", AdminNetsapiensAPICredentialsViewset)
router.register(r"api-credentials", NetsapiensAPICredentialsViewset)
router.register(r"cdr2-extracts", NetsapiensCdr2ExtractViewset, basename="cdr2-extracts")
router.register(r"subscription-clients", NetsapiensSubscriptionClientViewset, basename="subscription-clients")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<voip_provider_id>/<client_id>/call-subscription/", netsapiens_call_subscription_event_receiver_view, name="call-subscription"
    ),  # if we ever change this name, we must change NetsapiensSubscriptionClient#get_subscription_url
    # path('call-origid-subscription/', netsapiens_call_origid_subscription_event_receiver_view),
]
