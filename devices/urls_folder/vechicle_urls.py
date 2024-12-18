from django.urls import path
from devices.views import *
urlpatterns = [
    path('vehicles/<telemetry>', CarView.as_view()),
    path('vehicles/<telemetry>/device/<id>', GetSingleVehicle.as_view()),
    path('vehicles/', CarView.as_view()),
    path('vehicles/delete/<id>', CarView.as_view()),
    path('vehicles/update/<id>', CarView.as_view()),
    path('vehicles/command/<device_id>', DeviceCommand.as_view()),
    path('vehicles/<id>/createdevices/', DeviceSelectedAfterCarCreatedView.as_view()),
    path('vehicles/reorder/', VechicleSorters.as_view()),
    path('vehicles/geofence/<device_id>', GeofenceView.as_view()),
    path('vehicles/GetDeviceDetails/<device_id>', GetDeviceDetails.as_view()),
    path('vehicles/car_alarms/update/',UpdateCarAlarms.as_view()), 
    path('vehicles/createAlarm/<deviceId>',CreateCAlEachDevice.as_view()), 
    path('vehicles/updateAlarm/<deviceId>',CreateCAlEachDevice.as_view()), 
    path('vehicles/drivingstatistics/<device_id>',DrivingStats.as_view()), 
    path('vehicles/getCalculatorDetails/<device_id>',GetCalculatorDetails.as_view())
]