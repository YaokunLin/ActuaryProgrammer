from django.contrib import admin
from django.urls import path
from rest_framework import routers

from .views import ClientViewset

router = routers.DefaultRouter()

router.register(r"clients", ClientViewset)

urlpatterns = router.urls
