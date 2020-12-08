from django.contrib import admin
from django.urls import path
from rest_framework import routers

from .views import CadenceViewSet

router = routers.DefaultRouter()
router.register(r"cadences", CadenceViewSet)
