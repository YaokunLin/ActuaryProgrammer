from django.urls import path
from rest_framework import routers


from .views import (
    AdminUserViewset,
    AgentViewset,
    ClientViewset,
    LoginView,
    PatientViewset,
    PracticeTelecomViewSet,
    PracticeViewSet,
    UserViewset,
    AdminVoipProviderViewset,
)

router = routers.DefaultRouter()

router.register(r"agents", AgentViewset)
router.register(r"clients", ClientViewset)
router.register(r"patients", PatientViewset)
router.register(r"practices", PracticeViewSet, basename="practices")
router.register(r"practice-telecoms", PracticeTelecomViewSet)
router.register(r"users", AdminUserViewset)
router.register(r"voip-providers", AdminVoipProviderViewset, basename="voip-providers")

urlpatterns = [
    path("login", LoginView.as_view()),
]


urlpatterns += router.urls
