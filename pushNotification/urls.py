# urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('register_fcm_token/', RegisterFCMTokenView.as_view(), name='register_fcm_token'),
    path('unregister_fcm_token/', UnregisterFCMTokenView.as_view(), name='unregister_fcm_token'),
    path('flespi_webhook/', FlespiWebhookView.as_view(), name='flespi_webhook'),
]
