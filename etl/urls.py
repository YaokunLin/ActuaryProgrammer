from rest_framework import routers


from .views import NetsapiensCdrsExtractViewset, VeloxPatientExtractViewset

router = routers.DefaultRouter()


router.register(r"etl/netsapiens/cdrs", NetsapiensCdrsExtractViewset)
router.register(r"etl/velox/patients", VeloxPatientExtractViewset)

urlpatterns = router.urls
