from django.db import models
import uuid
from auth_app.models import UserCustomModel
class CarAlarms(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    speedAlertEnabled=models.BooleanField(default=False)
    speedNotificationEnabled=models.BooleanField(default=False)
    vibrationAlertEnabled=models.BooleanField(default=True)
    vibrationNotificationEnabled=models.BooleanField(default=True)
    fuelAlertEnabled=models.BooleanField(default=False)
    fuelNotificationEnabled=models.BooleanField(default=False)
    rapidAccelerationAlertEnabled=models.BooleanField(default=True)
    rapidAccelerationNotificationEnabled=models.BooleanField(default=True)
    harshBrakingAlertEnabled=models.BooleanField(default=True)
    harshBrakingNotificationEnabled=models.BooleanField(default=True)
    hardBrakingAlertEnabled=models.BooleanField(default=False)
    hardBrakingNotificationEnabled=models.BooleanField(default=False)
    # collisionDetectionAlertEnabled=models.BooleanField(default=True)
    # collisionDetectionNotificationEnabled=models.BooleanField(default=False)
    aggressiveSteeringAlertEnabled=models.BooleanField(default=False)
    aggressiveSteeringNotificationEnabled=models.BooleanField(default=False)
    ignitionStatusAlertEnabled=models.BooleanField(default=False)
    ignitionStatusNotificationEnabled=models.BooleanField(default=False)
    batteryAlertEnabled=models.BooleanField(default=False)
    batteryNotificationEnabled=models.BooleanField(default=False)
    batteryChargingNotificationEnabled=models.BooleanField(default=True)
    batteryVoltageAlertEnabled=models.BooleanField(default=True)
    batteryVoltageNotificationEnabled=models.BooleanField(default=True)
    tamperAlertAlertEnabled=models.BooleanField(default=True)
    tamperAlertNotificationEnabled=models.BooleanField(default=True)
    batteryModeEnabled=models.BooleanField(default=True)
    powerSavingModeEnabled=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Alarms for Car: {self.id}"

class GeofenceAlarms(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id=models.CharField(max_length=255,null=True,blank=True)
    name=models.CharField(max_length=255,null=True,blank=True)
    longitude=models.CharField(max_length=255,null=True,blank=True)
    latitude=models.CharField(max_length=255,null=True,blank=True)
    radius=models.CharField(max_length=255,null=True,blank=True)
    alertOnEnter=models.BooleanField(default=True)
    alertOnExit=models.BooleanField(default=True)
    alertOnNotification=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Geofence Alarms: {self.name}"

# Create your models here.
class Device(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name=models.CharField(max_length=255)
    device_id = models.IntegerField(primary_key=True)
    device_type_id = models.IntegerField()
    fuelCalid=models.CharField(max_length=255,null=True)
    fuelThreshold=models.FloatField(default=0)
    batteryCalid=models.CharField(max_length=255,null=True)
    batteryThreshold=models.FloatField(default=0)
    speedCalid=models.CharField(max_length=255,null=True)
    speedThreshold=models.FloatField(default=0)
    hardBrakingCalid=models.CharField(max_length=255,null=True)
    hardBrakingSensitivity = models.CharField(
        max_length=255,null=True,default='moderate'
    )
    rapidAccelerationCalid=models.CharField(max_length=255,null=True)
    rapidAccelerationSensitivity = models.CharField(
        max_length=255,null=True,default='moderate'
    )
    batteryMode=models.CharField(max_length=255,null=True,default="active")
    powerModeType=models.CharField(max_length=255,null=True,blank=True,default="1")
    # harshBrakingSensitivity = models.CharField(
    #     max_length=6,
    #     choices=[
    #     ('LOW', 'Low'),
    #     ('MEDIUM', 'Medium'),
    #     ('HIGH', 'High'),
    # ],
    #     default='MEDIUM',
    # )
    ident = models.IntegerField(unique=True)
    status = models.CharField(max_length=10, choices=[
        ('selected', 'Selected'),
        ('unselected', 'Unselected'),
    ])
    notificationCount = models.IntegerField(default=0,null=True, blank=True)
    price=models.FloatField(null=True, blank=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
class UserSelectedDevice(models.Model):
    device_id = models.ForeignKey(Device, on_delete=models.CASCADE,related_name='device_selected_by_user')
    user = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE,related_name='user_selected_device')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Device: {self.device_id.name}, User: {self.user.first_name} {self.user.last_name}"
class Car(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) 
    priority = models.CharField(max_length=255,null=True,blank=True)
    vehicleImage = models.ImageField(null=True,blank=True,upload_to='vehicle_images/',default='vehicle_images/black-car-vector.png') 
    # vehicleImage = models.CharField(null=True,blank=True,max_length=255)
    vinNumber = models.CharField(max_length=17) 
    model = models.CharField(max_length=255) 
    year = models.IntegerField()
    make = models.CharField(max_length=255)
    nickName = models.CharField(max_length=255,null=True,blank=True)
    licensePlate = models.CharField(max_length=255,null=True,blank=True)
    odometerReading = models.CharField(max_length=255,null=True,blank=True)
    numberVehicle = models.CharField(max_length=255,null=True,blank=True)
    user = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE,related_name='user_car',null=True,blank=True)
    CarAlarms=models.ForeignKey(CarAlarms, on_delete=models.CASCADE,related_name='CarAlarms', null=True, blank=True)
    price=models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.nickName or str(self.model) + str(self.year) 
class UserCarsWithDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.OneToOneField(Car, on_delete=models.CASCADE,related_name='car_selected_by_user',null=True,blank=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE,related_name='device_selected_by_car',null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Car: {self.car.nickName}"

class DeviceTypeId(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deviceName = models.CharField(max_length=255)
    deviceTypeId = models.CharField(max_length=255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)