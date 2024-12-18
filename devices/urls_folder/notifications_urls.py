from django.urls import path
from devices.views import *
urlpatterns = [
    path('notifications/devices/<id>', GetNotification.as_view()),
    path('NotificationGeofence/<device_id>', GetNotificationsGeoFence.as_view()),
]