from rest_framework import routers

from .views import (
    CallViewset,
    CallerNameViewSet,
    CallLabelViewset,
)

router = routers.DefaultRouter()

router.register(r"calls", CallViewset)
router.register(r"caller_name", CallerNameViewSet)
router.register(r"labels", CallLabelViewset)

urlpatterns = router.urls
