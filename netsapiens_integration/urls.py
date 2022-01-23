from django.urls import include, path
from rest_framework import routers
from .views import (
    netsapiens_call_origid_subscription_view,
    netsapiens_call_subscription_view,
    NetsapiensCdr2ExtractViewset,
    NetsapiensSubscriptionClientViewset,
)

app_name = "netsapiens_integration"

router = routers.DefaultRouter()


router.register(r"netsapiens-subscription-clients", NetsapiensSubscriptionClientViewset, basename="netsapiens-subscription-clients")
router.register(r"netsapiens-cdr2-extracts", NetsapiensCdr2ExtractViewset, basename="netsapiens-cdr2-extracts")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<voip_provider_id>/<client_id>/call-subscription/", netsapiens_call_subscription_view, name="call-subscription"
    ),  # if we ever change this name, we must change NetsapiensSubscriptionClient#get_subscription_url
    # path('call-origid-subscription/', netsapiens_call_origid_subscription_view),
]
