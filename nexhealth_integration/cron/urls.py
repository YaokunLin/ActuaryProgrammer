from django.urls import path

from nexhealth_integration.cron.views import update_practices

app_name = "nexhealth_integration"

urlpatterns = [
    path(r"update-practices", update_practices, name="cron_nexhealth_update_practices"),
]
