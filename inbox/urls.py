from django.urls import path

from . import views


urlpatterns = [
    path("sms-messages/delivered-callback", views.SMSMessagesDeliveredCallbackView.as_view()),
    path("sms-messages/failed-callback", views.SMSMessagesFailedCallbackView.as_view()),
    path("sms-messages/<pk>", views.SMSMessageDetail.as_view()),
    path("sms-messages/", views.SMSMessagesView.as_view()),
    path("sms-messages", views.SMSMessageList.as_view()),
]
