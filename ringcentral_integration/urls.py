from django.urls import include, path
from rest_framework import routers

from .views import (
    webhook,
    LoginView
)


app_name = "ringcentral_integration"

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("webhook", webhook, name="webhook-receiver"),
    path("login", LoginView.as_view()),
]
