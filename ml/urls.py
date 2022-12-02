from django.urls import include, path
from rest_framework_nested import routers

from ml.views import MLFieldChoicesView, MLModelResultHistoryViewset, MLModelViewset

router = routers.SimpleRouter()

router.register(r"ml-models", MLModelViewset, basename="ml-models")
router.register(r"ml-model-result-history", MLModelResultHistoryViewset, basename="ml-model-result-history")


urlpatterns = [
    path(r"ml-field-choices", MLFieldChoicesView.as_view(), name="ml-field-choices"),
    path(r"", include(router.urls)),
]
