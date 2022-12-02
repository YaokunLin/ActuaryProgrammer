from django.urls import include, path
from rest_framework_nested import routers

from care.views import ProcedureViewset

router = routers.SimpleRouter()

router.register(r"procedures", ProcedureViewset, basename="call-procedures")


urlpatterns = [
    path(r"", include(router.urls)),
]
