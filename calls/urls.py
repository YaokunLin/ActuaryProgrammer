from rest_framework import routers

from .views import CallViewset, CallLabelViewset

router = routers.DefaultRouter()

router.register(r"calls", CallViewset)
router.register(r"labels", CallLabelViewset)

urlpatterns = router.urls
