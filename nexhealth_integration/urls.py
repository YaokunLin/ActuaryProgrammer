from django.urls import path

from nexhealth_integration.views import foo

app_name = "nexhealth_integration"

urlpatterns = [
    path("foo", foo, name="foo"),
]
