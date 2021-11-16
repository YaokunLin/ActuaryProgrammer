"""peerlogic URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path


from core.urls import urlpatterns as company_urlpatterns

from calls.urls import urlpatterns as call_urlpatterns
from inbox.urls import urlpatterns as inbox_urlpatterns
from reminders.urls import urlpatterns as reminders_urlpatterns


admin.site.site_header = "Peerlogic API Admin Portal"

urlpatterns = [
    path("api/reminders/", include(reminders_urlpatterns)),
    path("api/companies/", include(company_urlpatterns)),
    path("api/inbox/", include(inbox_urlpatterns)),
    path("api/calls/", include(call_urlpatterns)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("admin/", admin.site.urls),
]
