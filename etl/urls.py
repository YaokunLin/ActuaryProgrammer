from rest_framework import routers


from .views import NetsapiensCallExtractViewset, VeloxPatientExtractViewset

router = routers.DefaultRouter()


router.register(r"etl/netsapiens/cdrs", NetsapiensCallExtractViewset)
router.register(r"etl/velox/patients", VeloxPatientExtractViewset)

urlpatterns = router.urls
