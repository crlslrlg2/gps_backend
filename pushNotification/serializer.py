from rest_framework import serializers
from .models import FCMToken
from devices.models import Device
class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMToken
        fields = ['token', 'user','timezone']

class DeviceNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [ 'device_id', 'notificationCount']