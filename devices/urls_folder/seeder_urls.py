from django.urls import path
from devices.seeder import get_devices
urlpatterns = [
 path('upload-devices/', get_devices, name='upload-devices'),
]