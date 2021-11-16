from django.contrib import admin
from django.urls import path
from rest_framework import routers

from .views import CallViewset

router = routers.DefaultRouter()

router.register(r"", CallViewset)

urlpatterns = router.urls
