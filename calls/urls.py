from rest_framework import routers

from .views import (
    CallViewset,
    CallLabelViewset,
    TelecomCallerNameInfoViewSet,
)

router = routers.DefaultRouter()

router.register(r"calls", CallViewset)
router.register(r"labels", CallLabelViewset)
router.register(r"telecom_caller_name_info", TelecomCallerNameInfoViewSet)

urlpatterns = router.urls
