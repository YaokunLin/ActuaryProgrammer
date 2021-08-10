from django.urls import path

from . import views


urlpatterns = [
    path("sms-messages", views.SMSMessagesView.as_view()),
    path("sms-messages/<pk>", views.SMSMessageDetail.as_view()),
]
