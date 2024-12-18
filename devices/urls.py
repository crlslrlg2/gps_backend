from django.urls import path
from .views import *
from .seeder import get_devices
from devices.urls_folder import devices_urls,seeder_urls,vechicle_urls,notifications_urls,trips_urls
urlpatterns = [
    path('telemetry/<devSelector>/<temeletry>', TelemeryView.as_view()),
    path('updateSpeedLimits/<device_id>', UpdateSpeedLimitsView.as_view()),
    path('user/',userDataUpdate.as_view()),
] + devices_urls.urlpatterns + seeder_urls.urlpatterns + vechicle_urls.urlpatterns + notifications_urls.urlpatterns +trips_urls.urlpatterns