from django.urls import path
from rest_framework import routers


from .views import ClientViewset, LoginView, PatientViewset, PracticeTelecomViewSet, PracticeViewSet, VoipProviderViewset

router = routers.DefaultRouter()

router.register(r"clients", ClientViewset)
router.register(r"patients", PatientViewset)
router.register(r"practices", PracticeViewSet)
router.register(r"practice-telecoms", PracticeTelecomViewSet)
router.register(r"voip-providers", VoipProviderViewset, basename="voip-providers")

urlpatterns = [
    path("login", LoginView.as_view()),
]


urlpatterns += router.urls