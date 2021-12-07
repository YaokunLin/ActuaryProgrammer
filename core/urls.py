from rest_framework import routers


from .views import ClientViewset, ContactViewset

router = routers.DefaultRouter()

router.register(r"clients", ClientViewset)
router.register(r"contacts", ContactViewset)

urlpatterns = router.urls
