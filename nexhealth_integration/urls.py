from django.urls import path

from nexhealth_integration.views import ingest_practice, sync_practice

app_name = "nexhealth_integration"

urlpatterns = [
    path(r"ingest-practice", ingest_practice, name="nexhealth_ingest_practice"),
    path(r"sync-practice", sync_practice, name="nexhealth_sync_practice"),
]
