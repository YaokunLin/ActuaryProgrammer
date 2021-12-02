from rest_framework import routers


from .views import ClientViewset, ContactViewSet

router = routers.DefaultRouter()

router.register(r"clients", ClientViewset)
router.register(r"Contacts", ContactViewSet)

urlpatterns = router.urls
