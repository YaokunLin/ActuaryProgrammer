from django.urls import path

from nexhealth_integration.views import initialize_practice

app_name = "nexhealth_integration"

urlpatterns = [
    path(r"initialize-practice", initialize_practice, name="nexhealth_initialize_practice"),
]
