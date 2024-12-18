# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FCMToken
from auth_app.models import *
from .serializer import FCMTokenSerializer
from auth_app.serializer import UserSerializer
from .notifications import send_expo_notification
from devices.models import *
from rest_framework.permissions import AllowAny
from backend.utils import *
from django.shortcuts import get_object_or_404
import json
import re
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from rest_framework.decorators import api_view

class RegisterFCMTokenView(APIView):
    def post(self, request):
        try:
            data = request.data
            user = UserCustomModel.objects.get(id=request.user.id)
            token, created = FCMToken.objects.get_or_create(user=user, token=data['token'],timezone=data['timezone'])
            return Response({'status': 'Token registered'}, status=status.HTTP_201_CREATED)
        except UserCustomModel.DoesNotExist:
            return Response({'status': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except KeyError:
            return Response({'status': 'Invalid request data'}, status=status.HTTP_400_BAD_REQUEST)

class UnregisterFCMTokenView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            data = request.data
            # user = UserCustomModel.objects.get(email=data['email'])
            token_instance = FCMToken.objects.filter(user=request.user, token=data['token'])
            if token_instance.exists():
                token_instance.delete()
                return Response({'status': 'Token unregistered'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'Token not found'}, status=status.HTTP_404_NOT_FOUND)
        except KeyError:
            return Response({'status': 'Invalid request data'}, status=status.HTTP_400_BAD_REQUEST)


    
class FlespiWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # try:
            data = request.data
            device_id = data.get('device_id')
            body = data.get('notificationBody')
            alert = data.get('alert')
            geofence = data.get('geofence')
            is_trip_active_detector= data.get('is_trip_active_detector')
            timestamp = data.get('timestamp')

            # Ensure body is processed correctly
            body = self.round_deceleration_in_body(body)

            # Handle missing or invalid device_id
            if not device_id or device_id == 'null':
                return Response({'status': 'Device id is missing'}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the device object
            device = Device.objects.filter(device_id=device_id).first()
            if not device:
                return Response({'status': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

            # Fetch the related car
            car = self.get_car_by_device_id(device_id)
            # print(car,' carrr carrr arrrr')
            if not car:
                return Response({'status': 'Car not found for device'}, status=status.HTTP_404_NOT_FOUND)

            car_alarms = car.CarAlarms
            event = ""
            # Handle geofence event
            if is_trip_active_detector!='null':
                # if not car_alarms.tripActiveNotificationEnabled:
                #     return Response({'status': f'Trip Active Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)
                if is_trip_active_detector:
                    alert="Trip Start Alert"
                    
                    body = f"{device.name} {alert}"
                else:
                    alert="Trip End Alert"
                    
                    body = f"{device.name} {alert}"


            if geofence and geofence != 'null':
                geofence_details =GeofenceAlarms.objects.filter(name=geofence,device_id=device_id).first() 
                if not geofence_details:
                    return Response({'status': f'Geofence not found for {device_id}'}, status=status.HTTP_404_NOT_FOUND)
                if not geofence_details.alertOnNotification:
                    return Response({'status': f'Geofence Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)
                    
                alert="Geofence Alert"
                event = get_geofence_events(device_id, data)
                if event == "entered":
                    if not geofence_details.alertOnEnter:
                        return Response({'status': f'Geofence Alert On enter not enabled for {device_id}'},status=status.HTTP_400_BAD_REQUEST)
                    body = f"{device.name} Entered geofence {geofence}"
                else:
                    if not geofence_details.alertOnExit:
                        return Response({'status': f'Geofence Alert Off Exit not enabled for {device_id}'},status=status.HTTP_400_BAD_REQUEST)
                    body = f"{device.name} Exited geofence {geofence}"



            user_device = UserSelectedDevice.objects.filter(device_id=device.device_id).first()
            distanceUnit = user_device.user.distanceUnit
            if alert == "speed":
                alert = "Speed Alert"
                if not car_alarms.speedNotificationEnabled:
                    return Response({'status': f'Speed Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)

                current_speed_match = re.search(r'current speed of ([\d.]+)\s*km/h', body)
                if device.speedThreshold and current_speed_match:
                    if distanceUnit == 'metric':
                        current_speed = current_speed_match.group(1)
                        body = f"{device.name} is speeding: {round(current_speed)} km/h vs. {round(device.speedThreshold)} km/h limit."
                    else:
                        current_speed = current_speed_match.group(1)
                        kmh_to_mph = 0.621371
                        speed_threshold_mph = float(device.speedThreshold) * float(kmh_to_mph)
                        print("herer",current_speed,kmh_to_mph)
                        current_speed_mph = float(current_speed) * float(kmh_to_mph)
                        body = f"{device.name} is speeding: {round(current_speed_mph)} mph vs. {round(speed_threshold_mph)} mph limit."

            # CHECK IT
            elif alert == "fuel":
                alert = "Low Fuel Alert"
                print(device.fuelThreshold,'device device device')
                if not car_alarms.fuelNotificationEnabled:
                    return Response({'status': f'Fuel Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)
            elif alert == "hard_braking":  
                alert = "Hard Braking Alert"
                body = f"{device.name} detected hard braking exceeding {device.hardBrakingSensitivity} sensitivity level."
                if not car_alarms.hardBrakingNotificationEnabled:
                    return Response({'status': f'Hard braking Alert not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)
            elif alert == "vibration":  
                alert = "Vibration Alert"
                if not car_alarms.vibrationNotificationEnabled:
                    return Response({'status': f'Vibration Alert not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)
            elif alert == "harsh_braking":
                alert = "Harsh Braking Alert"
                if not car_alarms.harshBrakingNotificationEnabled:
                    return Response({'status': f'Harsh braking Alert not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)
            elif alert == "ignition_on" or alert == 'ignition_off':    
                alert = "Ignition Alert"
                if not car_alarms.ignitionStatusNotificationEnabled:
                    return Response({'status': f'Ignition Alert not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)
            # elif alert == "collision_detection":    
            #     alert = "Collision Detection Alert"
            #     if not car_alarms.collisionDetectionNotificationEnabled:
            #         return Response({'status': f'Collision Detection Alert not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)
            elif alert == "tamper":    
                alert = "Tamper Alert"
                if not car_alarms.tamperAlertNotificationEnabled:
                    return Response({'status': f'Tamper Alert not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)
            elif alert=="low_battery_voltage" or alert =="high_battery_voltage":    
                alert = "Battery Voltage Alert"
                if not car_alarms.batteryVoltageNotificationEnabled:
                    return Response({'status': f'batteryvoltage not enabled {device_id}'},status=status.HTTP_400_BAD_REQUEST)

            elif alert == "battery":
                alert = "Low Battery Alert"
                battery_percentage=int(data.get('battery_percentage'))
                if battery_percentage <= 10:
                    alert = "Critical Battery Alert"
                    body = f"{device.name} battery level is Critical. Current battery level: {battery_percentage}%"
                
                
                    
                if not car_alarms.batteryNotificationEnabled:
                    return Response({'status': f'Battery Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)

            elif alert == "rapid_acceleration":
                alert = "Rapid Acceleration Alert"
                # current_speed_match = re.search(r'current speed of ([\d.]+)\s*km/h', body)
                body = f"{device.name} detected rapid acceleration exceeding {device.rapidAccelerationSensitivity} sensitivity level."
                if not car_alarms.rapidAccelerationNotificationEnabled:
                    return Response({'status': f'Rapid Acceleration Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)
            elif alert == "power_status":
                alert = "Power Status Alert"
                if not car_alarms.batteryChargingNotificationEnabled:
                    return Response({'status': f'Power Status Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)
            elif alert == "aggressive_steering":
                alert = "Aggressive Steering Alert"
                body = f"{device.name} detected Aggressive Steering"
                if not car_alarms.aggressiveSteeringNotificationEnabled:
                    return Response({'status': f'Aggressive Steering Alert not enabled for {device_id}'}, status=status.HTTP_400_BAD_REQUEST)
            
            
            # Fetch the user related to the car and send the notification
            try:
                user_car_device = UserCarsWithDevice.objects.get(device_id=device_id)
                user = user_car_device.car.user
            except UserCarsWithDevice.DoesNotExist:
                return Response({'status': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)
            # print(body)
            # Send the notification
            title = alert
            message = body
            # tokens = ["ExponentPushToken[a9qkRQLzkyhfw3eW_8ZvIm]"]
            token_user=FCMToken.objects.filter(user=user)
            device.notificationCount += 1
            device.save()
            print(alert,body)

            # Send WebSocket notification to the user's group
            if user_device:
                self.send_websocket_notification(user_device.user.id)

            for token in token_user:
                try:
                    user_timezone = token.timezone
                    print(user_timezone)
                    print(token.token,title,message,timestamp,)
                    send_expo_notification(token.token, title, message,timestamp,user_timezone)
                except ValueError as e:
                    print(f"Invalid token: {token}, error: {e}")

            return Response({'status': 'Notification sent'}, status=status.HTTP_200_OK)
        # except Exception as e:
        #     # print(f"Error sending notification: {e}")
        #     return Response({'status': 'Error sending notification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def get_car_by_device_id(self, device_id):
        try:
            user_car_with_device = get_object_or_404(UserCarsWithDevice, device__device_id=device_id)
            
            return user_car_with_device.car
        except Exception as e:
            print(e,'eeeeeeeeeee')


    def send_websocket_notification(self, user_id):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                'type': 'notification_message',
            }
        )

    def round_deceleration_in_body(self, body):
        deceleration_match = re.search(r'Deceleration:\s*([-\d.]+)e?[-+]?\d*\s*m/s²', body)
        if deceleration_match:
            deceleration_value = float(deceleration_match.group(1))
            rounded_deceleration = round(deceleration_value)
            body = body.replace(deceleration_match.group(0), f"Deceleration: {rounded_deceleration} m/s²")
        return body





