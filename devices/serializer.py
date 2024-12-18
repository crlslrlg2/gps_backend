from rest_framework import serializers
from .models import *
import datetime
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'
    
    # def validate(self, validated_data):
    #     if len(str(validated_data['ident'])) < 15:
    #         raise serializers.ValidationError("Device IMEI cannot be less than 15")
    #     elif len(str(validated_data['ident'])) > 15:
    #         raise serializers.ValidationError("Device IMEI cannot be greater than 15")
    #     return validated_data

class UserSelectedDeviceSerializer(serializers.ModelSerializer):
    device = DeviceSerializer()
    
    class Meta:
        model = UserSelectedDevice
        fields = '__all__'
class DeviceIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['device_id']
class UserCarsWithDeviceSerializer(serializers.ModelSerializer):
    # device = DeviceSerializer()
    device = DeviceIDSerializer()
    
    class Meta:
        model = UserCarsWithDevice
        fields = ['device']


class CarSerializer(serializers.ModelSerializer):
    deviceId = serializers.SerializerMethodField()
    ident = serializers.SerializerMethodField()
    deviceTypeId = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = '__all__'
        read_only_fields = ('deviceId','ident','deviceTypeId')
        depth=1
    
        
    def get_deviceId(self, obj):
        user_car_device = UserCarsWithDevice.objects.filter(car=obj).first()
        if user_car_device and user_car_device.device:
            return user_car_device.device.device_id
        return None
    def get_ident(self, obj):
        user_car_device = UserCarsWithDevice.objects.filter(car=obj).first()
        if user_car_device and user_car_device.device:
            return user_car_device.device.ident
        return None
    def get_deviceTypeId(self, obj):
        user_car_device = UserCarsWithDevice.objects.filter(car=obj).first()
        if user_car_device and user_car_device.device:
            return user_car_device.device.device_type_id
        return None

    def validate(self, validated_data):
        if validated_data.get('odometerReading'):
            if int(validated_data['odometerReading']) < 0:
                raise serializers.ValidationError("Odometer reading cannot be negative")
        if validated_data.get('vinNumber'):
            if len(validated_data['vinNumber']) < 17:
                raise serializers.ValidationError("Vin Number cannot be less than 17 characters")
        return validated_data
    def create(self, validated_data):
        car_alarms_data = {
          "speedAlertEnabled":False,
          "speedNotificationEnabled":False,
          "fuelAlertEnabled":False,
          "fuelNotificationEnabled":False,
          "rapidAccelerationAlertEnabled":True,
          "rapidAccelerationNotificationEnabled":True,
          "harshBrakingAlertEnabled":True,
          "harshBrakingNotificationEnabled":True,
        #   "collisionDetectionAlertEnabled":True,
        #   "collisionDetectionNotificationEnabled":True,
          "ignitionStatusAlertEnabled":True,
          "ignitionStatusNotificationEnabled":True,
          "batteryAlertEnabled":False,
          "batteryNotificationEnabled":False,
          "vibrationAlertEnabled":True,
          "vibrationNotificationEnabled":True,
          # "tamperAlertSensitivity":"high",
          # "tamperAlertEnabled":True,
        #   "harshBrakingSensitivity":"medium",
        #   "hardBrakingSensitivity":"moderate",
        "aggressiveSteeringAlertEnabled":True,
        "aggressiveSteeringNotificationEnabled":True,
          "batteryVoltageAlertEnabled":True,
          "batteryVoltageNotificationEnabled":True,
          "tamperAlertAlertEnabled":True,
          "tamperAlertNotificationEnabled":True,
          "powerSavingModeEnabled":True,
         
        }
        car_alarms = CarAlarms.objects.create(**car_alarms_data)
        validated_data['CarAlarms'] = car_alarms
        car = super().create(validated_data)
        return car

class GeofenceAlarmsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeofenceAlarms
        fields = '__all__'
    

class CarAlarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarAlarms
        fields = '__all__'


class DeviceTypeIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceTypeId
        fields = '__all__'
