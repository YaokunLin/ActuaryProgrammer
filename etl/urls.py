from rest_framework import routers


from .views import ETLViewset

router = routers.DefaultRouter()

router.register(r"etl", ETLViewset)

urlpatterns = router.urls