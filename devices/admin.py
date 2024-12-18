from django.contrib import admin
from .models import CarAlarms, GeofenceAlarms, Device, UserSelectedDevice, Car, UserCarsWithDevice, DeviceTypeId

# Admin customization for CarAlarms
class CarAlarmsAdmin(admin.ModelAdmin):
    list_display = ['id', 'speedAlertEnabled', 'fuelAlertEnabled', 'batteryAlertEnabled', 'created_at', 'updated_at']
    list_filter = ['speedAlertEnabled', 'fuelAlertEnabled', 'batteryAlertEnabled']
    search_fields = ['id', 'speedAlertEnabled', 'fuelAlertEnabled', 'batteryAlertEnabled']
    ordering = ['created_at']

# Admin customization for GeofenceAlarms
class GeofenceAlarmsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'alertOnEnter', 'alertOnExit', 'alertOnNotification', 'created_at', 'updated_at']
    list_filter = ['alertOnEnter', 'alertOnExit', 'alertOnNotification']
    search_fields = ['name', 'device_id']

# Admin customization for Device
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_id', 'device_type_id', 'status', 'price']
    list_filter = ['status', 'device_type_id']
    search_fields = ['name', 'device_id']
 # Now ordering by 'created_at'

# Admin customization for UserSelectedDevice
class UserSelectedDeviceAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'user', 'created_at']
    search_fields = ['device_id__name', 'user__first_name', 'user__last_name']

# Admin customization for Car
class CarAdmin(admin.ModelAdmin):
    list_display = ['vinNumber', 'model', 'make', 'year', 'nickName', 'licensePlate', 'odometerReading', 'user', 'price', 'created_at']
    list_filter = ['year', 'make', 'model']
    search_fields = ['vinNumber', 'licensePlate', 'nickName']
    ordering = ['created_at']  # Sorting by 'created_at'

# Admin customization for UserCarsWithDevice
class UserCarsWithDeviceAdmin(admin.ModelAdmin):
    list_display = ['car', 'device', 'created_at']
    search_fields = ['car__nickName', 'device__name']

# Admin customization for DeviceTypeId
class DeviceTypeIdAdmin(admin.ModelAdmin):
    list_display = ['deviceName', 'deviceTypeId', 'created_at']
    search_fields = ['deviceName', 'deviceTypeId']

# Register the models with the admin site
admin.site.register(CarAlarms, CarAlarmsAdmin)
admin.site.register(GeofenceAlarms, GeofenceAlarmsAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(UserSelectedDevice, UserSelectedDeviceAdmin)
admin.site.register(Car, CarAdmin)
admin.site.register(UserCarsWithDevice, UserCarsWithDeviceAdmin)
admin.site.register(DeviceTypeId, DeviceTypeIdAdmin)
