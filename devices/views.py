from rest_framework.views import APIView
from .models import *
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from .serializer import *
import requests
from django.conf import settings
import json
from rest_framework import status
from auth_app.models import UserCustomModel
from auth_app.serializer import UserSerializer
from django.shortcuts import get_object_or_404
import datetime
import math
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from backend.utils import *
from devices.view.device_views import *
from devices.view.trip_views import *
from devices.view.geofence_views import *
from devices.view.alarm_views import *

# Create your views here.



def get_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    
    Parameters:
    lat1 (float): Latitude of the first point.
    lon1 (float): Longitude of the first point.
    lat2 (float): Latitude of the second point.
    lon2 (float): Longitude of the second point.

    Returns:
    float: Distance between the two points in meters.
    """
    R = 6371000  # Radius of the Earth in meters
    
    # Convert latitude and longitude from degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula to calculate the distance
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

class GetNotification(APIView):
    
    authentication_classes = [JWTAuthentication]

    def convert_timestamp_to_readable(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


    def get_car_by_device_id(self,device_id):
            user_car_with_device = get_object_or_404(UserCarsWithDevice, device__device_id=device_id)
            return user_car_with_device.car
     # Updated Change
   
    def get(self, request, id=None):
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

        if str(id) == 'all':
            device_ids = UserSelectedDevice.objects.filter(user=request.user).values_list('device_id__device_id', flat=True)
            device_ids = list(map(str, device_ids))
        else:
            device_ids = [id]
            
        all_processed_data = []
        
        for device_id in device_ids:
            car = self.get_car_by_device_id(device_id)
            car_alarms = car.CarAlarms
            urls = {}
            device=Device.objects.filter(device_id=device_id).first()
            if car_alarms.speedAlertEnabled:
                if device.speedCalid:
                    urls["speed"] = f'https://flespi.io/gw/calcs/{device.speedCalid}/devices/{device_id}/intervals/all'
            if car_alarms.rapidAccelerationAlertEnabled:
                if device.rapidAccelerationCalid:
                    urls["rapid_acceleration"] = f'https://flespi.io/gw/calcs/{device.rapidAccelerationCalid}/devices/{device_id}/intervals/all'
            if car_alarms.harshBrakingAlertEnabled:
                urls["harsh_brake"] = f'https://flespi.io/gw/calcs/1701359/devices/{device_id}/intervals/all'
            if car_alarms.vibrationAlertEnabled:
                urls["vibration"] = f'https://flespi.io/gw/calcs/1711153/devices/{device_id}/intervals/all'
            if car_alarms.ignitionStatusAlertEnabled:
                urls["ignition_detection"] = f'https://flespi.io/gw/calcs/1702300/devices/{device_id}/intervals/all'
            if car_alarms.aggressiveSteeringAlertEnabled:
                urls['aggressive_steering'] = f'https://flespi.io/gw/calcs/1716456/devices/{device_id}/intervals/all'
            # if car_alarms.collisionDetectionAlertEnabled:
            #     urls['collision_detection'] = f'https://flespi.io/gw/calcs/1701842/devices/{device_id}/intervals/all'
            if car_alarms.fuelAlertEnabled:
                if device.fuelCalid:
                    urls['fuel'] = f'https://flespi.io/gw/calcs/{device.fuelCalid}/devices/{device_id}/intervals/all'
            if car_alarms.batteryAlertEnabled:
                if device.batteryCalid:
                    urls['battery'] = f'https://flespi.io/gw/calcs/{device.batteryCalid}/devices/{device_id}/intervals/all'
            if car_alarms.tamperAlertAlertEnabled:
                urls['temperAlert'] = f'https://flespi.io/gw/calcs/1709056/devices/{device_id}/intervals/all'
            if car_alarms.batteryVoltageAlertEnabled:
                urls['batteryVoltage'] = f'https://flespi.io/gw/calcs/1709063/devices/{device_id}/intervals/all'
            if car_alarms.hardBrakingAlertEnabled:
           
                if device.hardBrakingCalid:
                    urls['hardBraking'] = f'https://flespi.io/gw/calcs/{device.hardBrakingCalid}/devices/{device_id}/intervals/all'
            responses = {key: requests.get(url, headers=headers).json() for key, url in urls.items()}
        
            if any("errors" in response for response in responses.values()):
                # print(responses.values())
                # errors = next(response["errors"][0].get("reason") for response in responses.values() if "errors" in response)
                errors = next(response for response in responses.values() if "errors" in response)
                # print("Error")
                # print("responses",responses)
                return Response({"error": errors, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

            processed_data = []
            for alarm_type in ["ignition_detection", "battery", "fuel", "speed", "harsh_brake", "aggressive_steering","temperAlert","batteryVoltage","hardBraking","vibration","rapid_acceleration"]:
            # for alarm_type in ["ignition_detection", "battery", "fuel", "speed", "harsh_brake", "collision_detection","temperAlert","batteryVoltage","hardBraking"]:
                if alarm_type in responses:
                    processed_data += responses[alarm_type]["result"]

            for entry in processed_data:
                entry["timestamp"] = self.convert_timestamp_to_readable(int(entry["begin"]))
                
                if entry["alert"] == "speed":
                    entry["speed_limit"] = device.speedThreshold

            geofence_events = self.get_geofence_events([device_id])
            combined_data = processed_data + geofence_events
            all_processed_data.extend(combined_data)
            
        sorted_data = sorted(all_processed_data, key=lambda x: x['begin'], reverse=True)

        # Implementing pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(sorted_data, 10)  # 100 items per page

        try:
            paginated_data = paginator.page(page)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)
        
        return Response({
            "data": paginated_data.object_list,
            "page": paginated_data.number,
            "pages": paginator.num_pages,
            "total": paginator.count,
            "status": 200
        }, status=status.HTTP_200_OK)

    def get_geofence_events(self, device_ids):
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
        events = []
        print(device_ids)
        for device_id in device_ids:
            base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
            response = requests.get(base_url_cal, headers=headers)
            if response.status_code != 200:
                continue

            data = response.json()
            filtered_data = [item for item in data.get('result', []) if not item.get('auto_created')]
            filtered_calc_ids = [item['calc_id'] for item in filtered_data]

            IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
            if not IMEI:
                continue

            base_url_cal_check = "https://flespi.io/gw/calcs/all"
            response_all_calcs = requests.get(base_url_cal_check, headers=headers)
            if response_all_calcs.status_code != 200:
                continue

            all_calcs_data = response_all_calcs.json()
            matched_calculators = [
                calc for calc in all_calcs_data.get('result', [])
                if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
            ]

            if not matched_calculators:
                continue

            cal_id = matched_calculators[0]['id']
            geofence_data = matched_calculators[0]['selectors'][0]['geofences']

            

            last_interval_url = f"https://flespi.io/gw/calcs/{cal_id}/devices/{device_id}/intervals/all"
            response_last_interval = requests.get(last_interval_url, headers=headers)
            if response_last_interval.status_code != 200:
                continue

            last_interval_data = response_last_interval.json()

            for geofence in geofence_data:
                geofence_center = (geofence['center']['lat'], geofence['center']['lon'])
                geofence_radius = geofence['radius'] * 1000

                for interval in last_interval_data.get('result', []):
                    lat_in = interval.get('position.latitude.in')
                    lon_in = interval.get('position.longitude.in')
                    lat_out = interval.get('position.latitude.out')
                    lon_out = interval.get('position.longitude.out')
                    
                    if lat_in is None or lon_in is None or lat_out is None or lon_out is None:
                        continue
                    
                    distance_in = get_distance(lat_in, lon_in, geofence_center[0], geofence_center[1])
                    distance_out = get_distance(lat_out, lon_out, geofence_center[0], geofence_center[1])
                    
                    inside_in = distance_in <= int(geofence_radius)
                    inside_out = distance_out<= int(geofence_radius)
                    print("inside_in", int(distance_in),geofence_radius,inside_in)
                    print("inside_out", int(distance_out),geofence_radius,inside_out)
                    event = ""
                    # if inside_in and not inside_out:
                    if int(distance_in) < int(distance_out) and inside_in :
                        event = "exited"
                    elif int(distance_in) > int(distance_out) and inside_out:
                        event = "entered"
                    
                    if event=="exited":
                        try:
                            timestamp = float(interval.get('timestamp'))
                            timestamp_str = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            events.append({
                                "event": event,
                                "geofence_name": geofence['name'],
                                "timestamp": timestamp_str,
                                "device_id": device_id,
                                "alert":interval['alert'],
                                "begin":interval['begin'],
                                'id':interval['id'],
                                'nickName':interval.get('nickName',None),
                                "latitude" : interval.get('position.latitude.in'),
                                "longitude" : interval.get('position.longitude.in'),
                                "lat_out" : interval.get('position.latitude.out'),
                                "lon_out" : interval.get('position.longitude.out')
                            })
                        except (ValueError, TypeError):
                            continue
                    elif event=='entered':
                        try:
                            timestamp = float(interval.get('timestamp'))
                            timestamp_str = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            events.append({
                                "alert":interval['alert'],
                                "event": event,
                                "geofence": geofence['name'],
                                "timestamp": timestamp_str,
                                "device_id": device_id,
                                "begin":interval['begin'],
                                'id':interval['id'],
                                'nickName':interval.get('nickName',None),
                                "lat_in" : interval.get('position.latitude.in'),
                                "lon_in" : interval.get('position.longitude.in'),
                                "latitude" : interval.get('position.latitude.out'),
                                "longitude" : interval.get('position.longitude.out')
                                
                                
                                
                            })
                        except (ValueError, TypeError):
                            continue
        return events

class UpdateSpeedLimitsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request,device_id=None):
       
        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_url = f"https://flespi.io/gw/devices/{device_id}/settings"
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

        # Perform the GET request to retrieve settings
        check_response = requests.get(f"{base_url}/all", headers=headers)
        if check_response.status_code != 200:
            return Response({"error": "Failed to retrieve settings", "details": check_response.content.decode()}, status=status.HTTP_400_BAD_REQUEST)

        settings_data = check_response.json()
        existing_settings = settings_data.get("result", [])

        # Flags to check if speed alarms exist
        speed_alarm_exists = False
        overspeed_alarm_exists = False
        speed_check_exists = False

        # Check for any settings containing "speed" in their keys
        for setting in existing_settings:
            setting_name = setting.get("name")

            if setting_name == "speed":
                speed_alarm_exists = True

            elif setting_name == "overspeed_alarm":
                overspeed_alarm_exists = True

            elif setting_name == "speed_check":
                speed_check_exists = True

        if speed_alarm_exists or overspeed_alarm_exists or speed_check_exists:
            return Response({"message": "Speed-related alarms exist",'alarm':True, 
                             'status': 200}, 
                             status=status.HTTP_200_OK)
        else:
            return Response({"message": "No speed-related settings found.",'alarm':False, 
                             'status': 404}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request,device_id=None):
        new_high_speed_limit = request.data.get("highSpeedLimit", 120)  # Default to 120 if not provided
        new_low_speed_limit = request.data.get("lowSpeedLimit", 30)  # Default to 30 if not provided
        device_id = request.data.get('device_id', None)

        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_url = f"https://flespi.io/gw/devices/{device_id}/settings"
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

        # Perform the GET request to retrieve settings
        check_response = requests.get(f"{base_url}/all", headers=headers)
        if check_response.status_code != 200:
            return Response({"error": "Failed to retrieve settings", "details": check_response.content.decode()}, status=status.HTTP_400_BAD_REQUEST)

        settings_data = check_response.json()
        existing_settings = settings_data.get("result", [])

        # Responses to gather results
        responses = {}

        # Flags to check if speed alarms exist
        speed_alarm_exists = False
        overspeed_alarm_exists = False

        # Update any settings containing "speed" in their keys
        for setting in existing_settings:
            setting_name = setting.get("name")

            if setting_name == "speed_alarm":
                speed_alarm_exists = True
                update_payload = {
                    "address": "connection",
                    "properties": {
                        "high_alarm": {
                            "enable": True,
                            "limit": new_high_speed_limit
                        },
                        "low_alarm": {
                            "enable": True,
                            "limit": new_low_speed_limit
                        },
                        "speed_relay": {
                            "enable": False
                        }
                    }
                }
                response = requests.put(f"{base_url}/{setting_name}", headers=headers, data=json.dumps(update_payload))
                responses[setting_name] = response.status_code
                return Response({"message": "Speed Alarms is Updated", 'status': 200}, status=status.HTTP_200_OK)

            elif setting_name == "overspeed_alarm":
                overspeed_alarm_exists = True
                update_payload = {
                    "address": "connection",
                    "properties": {
                        "overspeed": {
                            "enable": True,
                            "limit": new_high_speed_limit,
                            "time": 30,  # Detection time interval (5 - 600 seconds)
                            "type": 0  # Alarm type (0 for GPRS, 1 for SMS and GPRS)
                        }
                    }
                }
                response = requests.put(f"{base_url}/{setting_name}", headers=headers, data=json.dumps(update_payload))
                return Response({"message": "Overspeed Alarms is Updated", 'status': 200}, status=status.HTTP_200_OK)

        if not speed_alarm_exists and not overspeed_alarm_exists:
            return Response({"error": "No speed-related settings found to update."}, status=status.HTTP_404_NOT_FOUND)
    
class userDataUpdate(APIView):
    def get(self, request):
        user = request.user
        try:
        # Validate and update user data
            serializer = UserSerializer(request.user)

            return Response({"data": serializer.data, "status":200}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
    def delete(self, request):
        user = UserCustomModel.objects.get(id=request.user.id)
        selected_devices = Device.objects.filter(device_selected_by_user__user=user)
        # devices=UserCarsWithDevice(car=user.user_car).values_list("device")
        # print(devices)
        for devices in selected_devices:
            devices.status="unselected"
            devices.save()
        # print(selected_devices)
        user.delete()
        return Response({"message": "User deleted successfully"}, status=status.HTTP_200_OK)
    def patch(self, request):
        user = request.user
        
        # Validate and update user data
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"user": serializer.data, "message": "User data successfully updated"}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



    





