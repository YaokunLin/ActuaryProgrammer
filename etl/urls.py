from django.urls import path
from rest_framework import routers

from .views import (NetsapiensCdrsExtractViewset, VeloxPatientExtractViewset,
                    netsapiens_call_origid_subscription_view,
                    netsapiens_call_subscription_view)

router = routers.DefaultRouter()


router.register(r"etl/netsapiens/cdrs", NetsapiensCdrsExtractViewset)
router.register(r"etl/velox/patients", VeloxPatientExtractViewset)

urlpatterns = router.urls

urlpatterns += [
    path("etl/netsapiens/call-subscription", netsapiens_call_subscription_view),
    path("etl/netsapiens/call-origid-subscription", netsapiens_call_origid_subscription_view),
]
