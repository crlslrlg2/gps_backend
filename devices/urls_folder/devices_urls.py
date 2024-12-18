from django.urls import path
from devices.views import *
urlpatterns = [
    path('devices/', DeviceView.as_view()),
    path('devices/<id>', DeviceView.as_view()),
    path('getDevicesTypes/',DevicesTypes.as_view()),
    path('getDevices/',DeviceTypeIdView.as_view()),
    path('getDevices/<pk>',DeviceTypeIdView.as_view()),
]