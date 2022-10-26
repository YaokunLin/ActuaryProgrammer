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

from calls.urls import urlpatterns as calls_urlpatterns
from care.urls import urlpatterns as care_urlpatterns
from core.urls import urlpatterns as core_urlpatterns
from etl.urls import urlpatterns as etl_urlpatterns
from inbox.urls import urlpatterns as inbox_urlpatterns
from ml.urls import urlpatterns as ml_urlpatterns
from reminders.urls import urlpatterns as reminders_urlpatterns

admin.site.site_header = "Peerlogic API Admin Portal"

integration_url_patterns = [
    path("jive/", include("jive_integration.urls", namespace="jive")),
    path("netsapiens/", include("netsapiens_integration.urls", namespace="netsapiens")),
    path("ringcentral/", include("ringcentral_integration.urls", namespace="ringcentral")),
]

urlpatterns = [
    path("admin/clearcache/", include("clearcache.urls")),
    path("admin/", admin.site.urls),
    path("api-docs/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/integrations/", include(integration_url_patterns)),
    path("api/", include(calls_urlpatterns)),
    path("api/", include(care_urlpatterns)),
    path("api/", include(core_urlpatterns)),
    path("api/", include(etl_urlpatterns)),
    path("api/", include(inbox_urlpatterns)),
    path("api/", include(ml_urlpatterns)),
    path("api/", include(reminders_urlpatterns)),
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]
