
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
import requests
from devices.models import *
from devices.serializer import *

from django.shortcuts import get_object_or_404

import time

from backend.utils import *

class CreateCAlEachDevice(APIView):    
    # permission_classes = [AllowAny]
    

    def post(self, request,deviceId=None):
        device_id = deviceId
        type_calculator = request.data.get('alarmType')
        threshold = request.data.get('threshold')
        device = Device.objects.filter(device_id=device_id).first()
         # Get the device
        device = get_object_or_404(Device, device_id=device_id) 
        car_alarms=UserCarsWithDevice.objects.filter(device=device).first()
        car_alarms=car_alarms.car.CarAlarms
        # print(car_alarms)
        serializer = CarAlarmSerializer(car_alarms, data=request.data)
        if serializer.is_valid():
            serializer.save()
        
        url_cal_creation = "https://flespi.io/gw/calcs"
        headers = {
            "Authorization": f"FlespiToken {settings.FLESPI_TOKEN}",
            "Content-Type": "application/json"
        }
        # print("c",type_calculator,device_id,threshold)
        payload = self.get_payload(device_id, type_calculator, threshold)
        # print("Payload",payload)
        if not payload:
            return Response({"error": "Invalid calculator type"}, status=400)

        response = requests.post(url_cal_creation, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            calculator_id = data['result'][0]['id']
            if type_calculator == 'fuel':
                device.fuelCalid = calculator_id
                device.fuelThreshold=threshold
            elif type_calculator == 'battery':
                device.batteryCalid = calculator_id
                device.batteryThreshold=threshold
            elif type_calculator == 'speed':
                device.speedCalid = calculator_id
                device.speedThreshold=threshold
            elif type_calculator == 'hardbraking':
                device.hardBrakingCalid = calculator_id
                device.hardBrakingSensitivity=threshold
            elif type_calculator == 'rapid_acceleration':
                device.rapidAccelerationCalid = calculator_id
                device.rapidAccelerationSensitivity=threshold
            
            print("Calculator successfully created with ID:", calculator_id)
            url_assign_calculator = f"https://flespi.io/gw/calcs/{calculator_id}/devices/{device_id}"
            assign_response = requests.post(url_assign_calculator, headers=headers, json={})
            
            if assign_response.status_code == 200:
                device.save()
                print(f" {type_calculator.capitalize() } Alarm successfully assigned to device {device.name}.")
                return Response({"message":f" {type_calculator.capitalize() } Alarm successfully assigned to device {device.name}."}, status=200)
            else:
                print(f"Failed to assign calculator to device. Status code: {assign_response.status_code}")
                print("Response:", assign_response.text)
                return Response({"error": "Failed to assign calculator"}, status=assign_response.status_code)
        else:
            print(f"Failed to create calculator. Status code: {response.status_code}")
            print("Response:", response.text)
            return Response({"error": "Failed to create calculator"}, status=response.status_code)
    
    def get_payload(self, device_id, type_calculator, threshold):
        device=Device.objects.filter(device_id=device_id).first()
        IMEI=device.ident
        if type_calculator == "battery":
            return [{
          "intervals_ttl": 31536000,
          "update_delay": 30,
          "update_period": 604800,
          "update_onchange": True,
          "messages_source": {
            "source": "device"
          },
          "validate_message": "",
          "validate_interval": "",
          "name": f"Battery % alarm ({device_id})",
          "selectors": [
            {
              "expression": f"battery.level < {threshold}",
                 "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
              "name": "Battery limit threshold tracking",
              "type": "expression"
            }
          ],
          "intervals_rotate": 0,
          "counters": [
            {
              "method": "first",
              "name": "battery_percentage",
              "parameter": "battery.level",
              "type": "parameter"
            },
            {
              "method": "first",
              "name": "latitude",
              "parameter": "position.latitude",
              "type": "parameter"
            },
            {
              "method": "first",
              "name": "longitude",
              "parameter": "position.longitude",
              "type": "parameter"
            },
            {
              "method": "first",
              "name": "ident",
              "parameter": "ident",
              "type": "parameter"
            },
            {
              "name": "alert",
              "type": "specified",
              "value": "battery"
            },
            {
              "method": "first",
              "name": "osm",
              "parameter": "osm.address",
              "type": "parameter"
            },
            {
              "method": "first",
              "name": "nickName",
              "parameter": "device.name",
              "type": "parameter"
            },
            {
              "method": "first",
              "name": "device_id",
              "parameter": "device.id",
              "type": "parameter"
            },
            {
              "expression": "tostring($device.name) + ' has a low battery level of ' + tostring(battery.level) + '%.'",
              "method": "first",
              "name": "notificationBody",
              "type": "expression"
            },
            {
              "expression": "'Battery Level Alert'",
              "method": "first",
              "name": "notificationTitle",
              "type": "expression"
            },
              {
      "format": "%Y-%m-%d %H:%M:%S",
      "interval": "begin",
      "name": "event_time",
      "type": "datetime"
    }
          ],
          "timezone": "America/Los_Angeles",
          "metadata": {
                    "imei": str(IMEI)
                }
        }]
        elif type_calculator == 'fuel':
            return [{
                "intervals_ttl": 31536000,
                "update_delay": 30,
                "update_period": 604800,
                "update_onchange": True,
                "messages_source": {
                    "source": "device"
                },
                "validate_message": "",
                "validate_interval": "",
                "name": f"Fuel % alarm {device_id}",
                "selectors": [
                    {
                        "expression": f"(can.remaining.fuel.level < {threshold})",
                           "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        
                        "name": "Fuel limit threshold tracking",
                        "type": "expression"
                    }
                ],
                "intervals_rotate": 0,
                "counters": [
                    {
                        "method": "first",
                        "name": "fuel_percentage",
                        "parameter": "can.remaining.fuel.level",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "latitude",
                        "parameter": "position.latitude",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "longitude",
                        "parameter": "position.longitude",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "ident",
                        "type": "parameter"
                    },
                    {
                        "name": "alert",
                        "type": "specified",
                        "value": "fuel"
                    },
                    {
                        "method": "first",
                        "name": "fuel_threshold_percentage",
                        "parameter": "",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "osm",
                        "parameter": "osm.address",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "nickName",
                        "parameter": "device.name",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "device_id",
                        "parameter": "device.id",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "fuel_percentage1",
                        "parameter": "$fuel.level",
                        "type": "parameter"
                    },
                    {
                        "expression": "tostring($device.name) + ' has a low fuel level of ' + tostring(can.remaining.fuel.level) + '% .'",
                        "method": "first",
                        "name": "notificationBody",
                        "type": "expression"
                    },
                    {
                        "expression": "'Fuel Level Alert'",
                        "method": "first",
                        "name": "notificationTitle",
                        "type": "expression"
                    },
                     {
      "format": "%Y-%m-%d %H:%M:%S",
      "interval": "begin",
      "name": "event_time",
      "type": "datetime"
    }
                ],
                "timezone": "America/Los_Angeles",
                "metadata": {
                    "imei": str(IMEI)
                }
            }]
        elif type_calculator == 'speed':
            return [{
                "intervals_ttl": 31536000,
                "update_delay": 30,
                "update_period": 31536000,
                "update_onchange": True,
                "messages_source": {
                    "source": "device"
                },
                "validate_message": "",
                "validate_interval": "",
                "name": f"Speed Alarm {device_id}",
                "selectors": [
                    {
                        "expression": f"$position.speed > {threshold}",
                           "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        
                        "type": "expression"
                    }
                ],
                "intervals_rotate": 0,
                "counters": [
                    {
                        "expression": "$position.speed",
                        "method": "last",
                        "name": "current_speed",
                        "type": "expression"
                    },
                    {
                        "expression": "$position.speed",
                        "method": "maximum",
                        "name": "max_speed",
                        "type": "expression"
                    },
                    {
                        "expression": "$position.longitude",
                        "method": "last",
                        "name": "longitude",
                        "type": "expression"
                    },
                    {
                        "expression": "$position.latitude",
                        "method": "last",
                        "name": "latitude",
                        "type": "expression"
                    },
                    {
                        "expression": "1",
                        "method": "duration",
                        "name": "overspeed_duration",
                        "type": "expression"
                    },
                    {
                        "method": "first",
                        "name": "ident",
                        "type": "parameter"
                    },
                    {
                        "name": "alert",
                        "type": "specified",
                        "value": "speed"
                    },
                    {
                        "method": "last",
                        "name": "osm",
                        "parameter": "osm.address",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "nickName",
                        "parameter": "device.name",
                        "type": "parameter"
                    },
                    {
                        "method": "first",
                        "name": "device_id",
                        "parameter": "device.id",
                        "type": "parameter"
                    },
                    {
                        "expression": f"tostring($device.name) + ' has exceeded the speed limit with a current speed of ' + tostring($position.speed) + ' km/h.'",
                        "method": "first",
                        "name": "notificationBody",
                        "type": "expression"
                    },
                    {
                        "name": "notificationTitle",
                        "type": "specified",
                        "value": "Speed Alert"
                    },
                     {
      "format": "%Y-%m-%d %H:%M:%S",
      "interval": "begin",
      "name": "event_time",
      "type": "datetime"
    }
                ],
                "timezone": "America/Los_Angeles",
                "metadata": {
                    "imei": str(IMEI)
                }
            }]
        elif type_calculator == 'hardbraking':
            if threshold == 'moderate':
                threshold =-5
            elif threshold == 'excessive':
                threshold =-7
            elif threshold == 'light':
                threshold =-4
            return [{
              "intervals_ttl": 31536000,
              "update_delay": 30,
              "update_period": 604800,
              "update_onchange": True,
              "messages_source": {
                "source": "device"
              },
              "validate_message": "position.speed != null && position.valid",
              "validate_interval": "",
              "name": f"Hard Braking ({device_id})",
              "selectors": [
                {
                  "expression": f"($position.speed - previous('position.speed')) / (timestamp - previous('timestamp')) < {threshold}",
                  "max_messages_time_diff": 10,
                  "merge_message_after": True,
                  "merge_message_before": True,
                  "merge_unknown": True,
                  "method": "boolean",
                  "name": "Harsh Braking Threshold",
                  "type": "expression"
                }
              ],
              "intervals_rotate": 0,
              "counters": [
                {
                  "method": "first",
                  "name": "latitude",
                  "parameter": "position.latitude",
                  "type": "parameter"
                },
                {
                  "method": "first",
                  "name": "longitude",
                  "parameter": "position.longitude",
                  "type": "parameter"
                },
                {
                  "method": "first",
                  "name": "ident",
                  "parameter": "ident",
                  "type": "parameter"
                },
                {
                  "name": "alert",
                  "type": "specified",
                  "value": "hard_braking"
                },
                {
                  "expression": "($position.speed - previous('position.speed')) / (timestamp - previous('timestamp'))",
                  "method": "minimum",
                  "name": "max_deceleration",
                  "type": "expression"
                },
                {
                  "method": "first",
                  "name": "initial_speed",
                  "parameter": "position.speed",
                  "type": "parameter"
                },
                {
                  "method": "last",
                  "name": "final_speed",
                  "parameter": "position.speed",
                  "type": "parameter"
                },
                {
                  "expression": "1",
                  "method": "summary",
                  "name": "duration1",
                  "type": "expression"
                },
                {
                  "method": "first",
                  "name": "nickName",
                  "parameter": "device.name",
                  "type": "parameter"
                },
                {
                  "expression": "tostring($device.name) + ' detected hard braking. Deceleration: ' + tostring(($position.speed - previous('position.speed')) / (timestamp - previous('timestamp'))) + ' m/s². Initial speed: ' + tostring(previous('position.speed')) + ' km/h. Final speed: ' + tostring($position.speed) + ' km/h.'",
                  "method": "first",
                  "name": "notificationBody",
                  "type": "expression"
                },
                {
                  "expression": "'Hard Braking Detected'",
                  "method": "first",
                  "name": "notificationTitle",
                  "type": "expression"
                },
                {
                  "method": "first",
                  "name": "device_id",
                  "parameter": "device.id",
                  "type": "parameter"
                },
                 {
      "format": "%Y-%m-%d %H:%M:%S",
      "interval": "begin",
      "name": "event_time",
      "type": "datetime"
    }
              ],
              "timezone": "America/Los_Angeles",
              "metadata": {
                    "imei": str(IMEI)
                }
            }]
        
        elif type_calculator == 'rapid_acceleration':
            if threshold == 'moderate':
                 threshold ="$position.speed > 120 && $position.speed <= 150"
            elif threshold == 'excessive':
                threshold ="$position.speed > 150"
            elif threshold == 'light':
                threshold ="$position.speed > 100 && $position.speed <= 120"
            else:
               threshold ="$position.speed > 120 && $position.speed <= 150"
              
            return [{
              "intervals_ttl": 31536000,
              "update_delay": 30,
              "update_period": 31536000,
              "update_onchange": False,
              "messages_source": {
                "source": "device"
              },
              "validate_message": "",
              "validate_interval": "",
              "name": f"Rapid Acceleration ({device_id})",
             "selectors": [
                     {
                        "expression": f"({threshold})",
                         "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        "name": "Fuel limit threshold tracking",
                        "type": "expression"
                    }
                ],
              "intervals_rotate": 0,
              "counters": [
                {
                  "expression": "$position.speed",
                  "method": "last",
                  "name": "current_speed",
                  "type": "expression"
                },
                {
                  "expression": "$position.longitude",
                  "method": "last",
                  "name": "longitude",
                  "type": "expression"
                },
                {
                  "expression": "$position.latitude",
                  "method": "last",
                  "name": "latitude",
                  "type": "expression"
                },
                {
                  "expression": "1",
                  "method": "duration",
                  "name": "overspeed_duration",
                  "type": "expression"
                },
                {
                  "method": "first",
                  "name": "ident",
                  "type": "parameter"
                },
                {
                  "name": "alert",
                  "type": "specified",
                  "value": "rapid_acceleration"
                },
                {
                  "method": "last",
                  "name": "osm",
                  "parameter": "osm.address",
                  "type": "parameter"
                },
                {
                  "method": "first",
                  "name": "nickName",
                  "parameter": "device.name",
                  "type": "parameter"
                },
                {
                  "expression": "tostring($device.name) + ' detected rapid acceleration exceeding sensitivity level.'",
                  "method": "first",
                  "name": "notificationBody",
                  "type": "expression"
                },
                {
                  "name": "notificationTitle",
                  "type": "specified",
                  "value": " Alert"
                },
                {
                  "method": "first",
                  "name": "device_id",
                  "parameter": "device.id",
                  "type": "parameter"
                },
                 {
      "format": "%Y-%m-%d %H:%M:%S",
      "interval": "begin",
      "name": "event_time",
      "type": "datetime"
    }
              ],
              "timezone": "America/Los_Angeles",


              "metadata": {
                    "imei": str(IMEI)
                }
            }]
        else:
            return None
    def patch(self, request,deviceId=None):
        device_id = deviceId
        type_calculator = request.data.get('alarmType')
        threshold = request.data.get('threshold')
        cleaned_calculator={}
        
        # Get the device
        device = get_object_or_404(Device, device_id=device_id) 
        # matched_calculator
        # car_alarms=device.device_selected_by_car.car_id
        car_alarms=UserCarsWithDevice.objects.filter(device=device).first()
        car_alarms=car_alarms.car.CarAlarms
        # print(car_alarms)
        serializer = CarAlarmSerializer(car_alarms, data=request.data)
        if serializer.is_valid():
            # print(serializer.data)
            serializer.save()
        # calc_selector = matched_calculator['id']
        if all([device_id, type_calculator]):
            allowed_properties = [
                "name", "messages_source", "update_period", "update_delay", "update_onchange",
                "intervals_ttl", "intervals_rotate", "selectors", "counters", "validate_interval",
                "validate_message", "timezone", "metadata"
            ]
            calc_selector=''
            device=Device.objects.filter(device_id=device_id).first()
            IMEI=device.ident
            
            # Update the relevant threshold based on the type of calculator
            if type_calculator == 'fuel':
                device.fuelThreshold = threshold
                matched_calculator=self.get_payload(device_id, type_calculator,threshold)
                calc_selector=device.fuelCalid
                cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}
                cleaned_calculator["selectors"]=[]
                cleaned_calculator["selectors"] = [
                    {
                        "expression": f"can.remaining.fuel.level < {threshold}",
                           "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        "name": "Fuel limit threshold tracking",
                        "type": "expression"
                    }
                ]
            elif type_calculator == 'battery':
                device.batteryThreshold = threshold
                matched_calculator=self.get_payload(device_id, type_calculator,threshold)
                calc_selector=device.batteryCalid
                cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}
                cleaned_calculator["selectors"]=[]
                cleaned_calculator["selectors"] = [
                    {
                        "expression": f"battery.level < {threshold}",
                           "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        "name": "Battery limit threshold tracking",
                        "type": "expression"
                    }
                ]
            elif type_calculator == 'speed':
                device.speedThreshold = threshold
                matched_calculator=self.get_payload(device_id, type_calculator,threshold)
                calc_selector=device.speedCalid
                cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}
                print("cleaned_calculator",cleaned_calculator)
                cleaned_calculator["selectors"]=[]
                cleaned_calculator["selectors"] = [
                    {
                        "expression": f"$position.speed > {threshold}",
                           "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        "name": "Speed limit threshold tracking",
                        "type": "expression"
                    }
                ]
            elif type_calculator == 'hardbraking':
                device.hardBrakingSensitivity = threshold
                matched_calculator=self.get_payload(device_id, type_calculator,threshold)
                calc_selector=device.hardBrakingCalid
                cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}
                cleaned_calculator["selectors"]=[]
                if threshold == 'moderate':
                    threshold =-8
                elif threshold == 'excessive':
                    threshold =-12
                elif threshold == 'light':
                    threshold =-4
                cleaned_calculator["selectors"] = [
                          {
                            "expression": f"($position.speed - previous('position.speed')) / (timestamp - previous('timestamp')) < {threshold}",
                               "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                            "name": "Harsh Braking Threshold",
                            "type": "expression"
                          }
                        ]
            elif type_calculator == 'rapid_acceleration':
                device.rapidAccelerationSensitivity = threshold
                matched_calculator=self.get_payload(device_id, type_calculator,threshold)
                calc_selector=device.rapidAccelerationCalid
                cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}
                if threshold == 'moderate':
                    threshold ="$position.speed > 120 && $position.speed <= 150"
                elif threshold == 'excessive':
                    threshold ="$position.speed > 150"
                elif threshold == 'light':
                    threshold =f"$position.speed > {100} && $position.speed <= {120}"
                else:
                  threshold ="$position.speed > 120 && $position.speed <= 150"
                # print("cleaned_calculator",cleaned_calculator)
                cleaned_calculator["selectors"]=[]
                cleaned_calculator["selectors"] =[  {
                        "expression": f"({threshold})",
                          "max_inactive": 30,
      "method": "boolean",
      "min_duration": 1,
                        "method": "boolean",
                        "name": "Fuel limit threshold tracking",
                        "type": "expression"
                    }
                ]

            # Update the Flespi calculator with the new settings
            update_url = f"https://flespi.io/gw/calcs/{calc_selector}?fields=update_delay,update_period,update_onchange,validate_message,validate_interval,intervals_ttl,intervals_rotate,messages_source,metadata"
            headers = {
                "Authorization": f"FlespiToken {settings.FLESPI_TOKEN}",
                "Content-Type": "application/json"
            }
            # print(cleaned_calculator)
            response_update = requests.put(update_url, headers=headers, json=cleaned_calculator)
            #print(response_update.json())
            if response_update.status_code == 200:
               
                device.save()
                return Response({"message": f" {type_calculator.capitalize() } Alarm successfully assigned to device {device.name}."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Failed to update calculator", "details": response_update.text}, status=response_update.status_code)    
        return Response({"message": "Alarms Update Successfully", "status": status.HTTP_200_OK}, status=status.HTTP_200_OK) 
    # def delete(self, request):
    #     device_id = request.data.get('deviceId')
    #     type_calculator = request.data.get('alarmType')
    #     if device_id is None:
    #         return Response({"error": "Device ID is required"}, status=status.HTTP_400_BAD_REQUEST)


class GetCalculatorDetails(APIView):
    # permission_classes = [AllowAny]

    def get(self, request, device_id=None):
        if device_id is None:
            return Response({"error": "Device ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        device = get_object_or_404(Device, device_id=device_id)
        serializer = DeviceSerializer(device)
        user_car_with_device = UserCarsWithDevice.objects.select_related('car__CarAlarms').get(device=device)
        
        car_alarms = user_car_with_device.car.CarAlarms
        car_alarms_data = CarAlarmSerializer(car_alarms)
        combined_data = car_alarms_data.data.copy()
        combined_data.update(serializer.data)
        
        # Remove unnecessary fields
        combined_data.pop("created_at", None)
        combined_data.pop("updated_at", None)
        
        # Check for battery and fuel level existence

        # Retrieve additional device messages for the past day
        current_time = int(time.time())
        one_day_ago = current_time - 86400  # 86400 seconds in a day
        messages = self.retrieve_device_messages(device_id, one_day_ago, current_time)
        combined_data['device_messages'] = messages
        battery_exists = any('battery.level' in message for message in messages)
        fuel_level_exists = any('can.fuel.consumed' in message for message in messages)  # Replace 'can.fuel.consumed' with the actual key if different
        combined_data['battery_exists'] = battery_exists
        combined_data['fuel_level_exists'] = fuel_level_exists

        return Response({"data": combined_data, "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)

    def retrieve_device_messages(self, device_id, from_timestamp, to_timestamp):
        url = f"https://flespi.io/gw/devices/{device_id}/messages"
        headers = {
            'Authorization': f'FlespiToken {settings.FLESPI_TOKEN}',
        }
        params = {
            # 'from': from_timestamp,
            # 'to': to_timestamp,
            'fields': 'battery.level,can.fuel.level,fuel.level',
        }
        response = requests.get(url, headers=headers, json=params)
        print(response.json())
        if response.status_code == 200:
            # print("Device", device_id)
            return response.json().get('result', [])
        return []
