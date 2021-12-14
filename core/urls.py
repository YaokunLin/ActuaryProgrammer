from django.urls import include, path
from rest_framework import routers


from .views import ClientViewset, LoginView, PatientViewset

router = routers.DefaultRouter()

router.register(r"clients", ClientViewset)
router.register(r"patients", PatientViewset)

urlpatterns = [
    path("login/", LoginView.as_view()),
]


urlpatterns += router.urls
