from django.urls import path

from jive_integration.views import webhook, cron, authentication_callback, authentication_connect

app_name = "jive_integration"

urlpatterns = [
    path("auth/connect", authentication_connect, name="authentication-connect"),
    path("auth/callback", authentication_callback, name="authentication-callback"),
    path("webhook", webhook, name="webhook-receiver"),
    path("cron", cron, name="cron"),
]