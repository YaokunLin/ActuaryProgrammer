from rest_framework import routers

from .views import VeloxPatientExtractViewset

router = routers.DefaultRouter()


router.register(r"etl/velox/patients", VeloxPatientExtractViewset)

urlpatterns = router.urls
