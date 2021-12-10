from rest_framework import routers


from .views import ClientViewset, PatientViewset

router = routers.DefaultRouter()

router.register(r"clients", ClientViewset)
router.register(r"patients", PatientViewset)

urlpatterns = router.urls
