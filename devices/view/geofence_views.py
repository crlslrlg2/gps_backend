
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
import requests
from devices.models import *
from devices.serializer import *
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

import time

from backend.utils import *
class GetNotificationsGeoFence(APIView):

    def get(self, request, device_id):
        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
        base_url_cal_check = "https://flespi.io/gw/calcs/all"
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
        
        # Perform the GET request to retrieve device calculators
        response = requests.get(base_url_cal, headers=headers)
        if response.status_code != 200:
            return Response({"error": "Failed to retrieve data from Flespi."}, status=response.status_code)
        
        data = response.json()
        
        # Filter out the objects where auto_created is false
        filtered_data = [item for item in data.get('result', []) if not item.get('auto_created')]
        filtered_calc_ids = [item['calc_id'] for item in filtered_data]
        
        # Retrieve the device's IMEI
        try:
            IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
            if not IMEI:
                return Response({"error": "IMEI not found for the given device ID."}, status=status.HTTP_404_NOT_FOUND)
        except Device.DoesNotExist:
            return Response({"error": "Device not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Perform the GET request to retrieve all calculators
        response_all_calcs = requests.get(base_url_cal_check, headers=headers)
        if response_all_calcs.status_code != 200:
            return Response({"error": "Failed to retrieve all calculators from Flespi."}, status=response_all_calcs.status_code)
        
        all_calcs_data = response_all_calcs.json()
        
        # Filter all calculators to include only those with calc_id in filtered_calc_ids and name containing IMEI
        matched_calculators = [
            calc for calc in all_calcs_data.get('result', [])
            if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
        ]
        
        if not matched_calculators:
            return Response({"error": "No matched calculators found."}, status=status.HTTP_404_NOT_FOUND)
        
        cal_id = matched_calculators[0]['id']
        geofence_data = matched_calculators[0]['selectors'][0]['geofences']
        
        # Prepare parameters for the last interval URL
        params = {
            "count": 16,
            "reverse": "true"
        }
        
        # Fetch the last interval data for the matched calculator
        last_interval_url = f"https://flespi.io/gw/calcs/{cal_id}/devices/{device_id}/intervals/all"
        response_last_interval = requests.get(last_interval_url, headers=headers, params=params)
        
        if response_last_interval.status_code != 200:
            return Response({"error": "Failed to retrieve last interval data from Flespi."}, status=response_last_interval.status_code)
        
        last_interval_data = response_last_interval.json()
        
        # Initialize event list
        events = []
        triggered_intervals = []
        
        # Process geofence data
        for geofence in geofence_data:
            geofence_center = (geofence['center']['lat'], geofence['center']['lon'])
            geofence_radius = geofence['radius'] * 1000  # Convert to meters if needed
            print("Geofence",geofence)
            for interval in last_interval_data.get('result', []):
                lat_in = interval.get('position.latitude.in')
                lon_in = interval.get('position.longitude.in')
                lat_out = interval.get('position.latitude.out') 
                lon_out = interval.get('position.longitude.out')
                
                if lat_in is None or lon_in is None or lat_out is None or lon_out is None:
                    continue
                
                distance_in = get_distance(lat_in, lon_in, geofence_center[0], geofence_center[1])
                distance_out = get_distance(lat_out, lon_out, geofence_center[0], geofence_center[1])
                
                inside_in = distance_in <= geofence_radius
                inside_out = distance_out <= geofence_radius
                
                event = ""
                if inside_in and not inside_out:
                    event = "exited"
                elif not inside_in and inside_out:
                    event = "entered"
                
                if event:
                    interval["event"] = event
                    interval["geofence"] = geofence['name']
                    try:
                        timestamp = float(interval.get('timestamp'))
                        timestamp_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        interval["timestamp"] = timestamp_str
                        events.append({
                            "event": event,
                            "geofence": geofence['name'],
                            "timestamp": timestamp_str
                        })
                        triggered_intervals.append(interval)
                    except (ValueError, TypeError):
                        continue
                else:
                    interval["event"] = ""
                    interval["geofence"] = geofence['name']
                    try:
                        timestamp = float(interval.get('timestamp'))
                        timestamp_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        interval["timestamp"] = timestamp_str
                        # events.append({
                        #     "event": event,
                        #     "geofence": geofence['name'],
                        #     "timestamp": timestamp_str
                        # })
                        triggered_intervals.append(interval)
                    except (ValueError, TypeError):
                        continue

        # Sort triggered_intervals and events by timestamp
        triggered_intervals.sort(key=lambda x: x["timestamp"])
        events.sort(key=lambda x: x["timestamp"])
        
        return Response({'data': triggered_intervals, 'events': events}, status=status.HTTP_200_OK)

class GeofenceView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, device_id):
        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
        # base_url_cal_check = f"https://flespi.io/gw/calcs/all"
        # headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

        # # Perform the GET request to retrieve device calculators
        # response = requests.get(base_url_cal, headers=headers)
        # if response.status_code != 200:
        #     return Response({"error": "Failed to retrieve data from Flespi."}, status=response.status_code)

        # data = response.json()

        # # Filter out the objects where auto_created is false
        # filtered_data = [item for item in data['result'] if not item['auto_created']]
        # filtered_calc_ids = [item['calc_id'] for item in filtered_data]

        # # Retrieve the device's IMEI
        # try:
        #     IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
        #     if not IMEI:
        #         return Response({"error": "IMEI not found for the given device ID."}, status=status.HTTP_404_NOT_FOUND)
        # except Device.DoesNotExist:
        #     return Response({"error": "Device not found."}, status=status.HTTP_404_NOT_FOUND)

        # # Perform the GET request to retrieve all calculators
        # response_all_calcs = requests.get(base_url_cal_check, headers=headers)
        # if response_all_calcs.status_code != 200:
        #     return Response({"error": "Failed to retrieve all calculators from Flespi."}, status=response_all_calcs.status_code)

        # all_calcs_data = response_all_calcs.json()

        # # Filter all calculators to include only those with calc_id in filtered_calc_ids and name containing IMEI
        # matched_calculators = [
        #     calc['selectors'][0]['geofences'] for calc in all_calcs_data['result']
        #     if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
        # ]

        # # Convert lat and lon to full spelling
        
                

        # if not matched_calculators:
        #     return Response({'data': matched_calculators, 'status': status.HTTP_200_OK}, status=status.HTTP_200_OK)

        # Integrate with GeofenceAlarms model
        geofence_alarms = GeofenceAlarms.objects.filter(
            # name__in=[geofence['name'] for geofence in matched_calculators[0]],
            device_id=device_id
        )
        geofence_alarms_data = GeofenceAlarmsSerializer(geofence_alarms, many=True).data
        for geofence_alarm in geofence_alarms_data:
            geofence_alarm['center'] = {
                'longitude': geofence_alarm.pop('longitude'),
                'latitude': geofence_alarm.pop('latitude')
            }
            

        # response_data = {
        #     # 'flespi_geofences': matched_calculators[0],
        #     # 'geofence_alarms': geofence_alarms_data
        # }

        return Response({'data': geofence_alarms_data, 'status': status.HTTP_200_OK}, status=status.HTTP_200_OK)    
    
    
    def post(self, request, device_id):
        center = request.data.get('center')
        name = request.data.get('name')
        radius = float(request.data.get('radius'))
        type_ = request.data.get('type', 'circle')
        center={
        "lat": float(center.pop('latitude')),
        "lon": float(center.pop('longitude'))
        }
        # Additional geofence-specific information
        description = request.data.get('description', '')
        alert_on_enter = request.data.get('alertOnEnter', False)
        alert_on_exit = request.data.get('alertOnExit', False)
        alert_on_notification = request.data.get('alertOnNotification', False)

        if not all([center, name, radius]):
            return Response({"error": "center, name, and radius are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
        base_url_cal_check = "https://flespi.io/gw/calcs/all"
        url_cal_creation = "https://flespi.io/gw/calcs"
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

        # Retrieve device calculators
        response = requests.get(base_url_cal, headers=headers)
        if response.status_code != 200:
            return Response({"error": "Failed to retrieve data from Flespi."}, status=response.status_code)

        data = response.json()
        filtered_data = [item for item in data['result'] if not item['auto_created']]
        filtered_calc_ids = [item['calc_id'] for item in filtered_data]

        # Retrieve the device's IMEI
        try:
            IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
            if not IMEI:
                return Response({"error": "IMEI not found for the given device ID."}, status=status.HTTP_404_NOT_FOUND)
        except Device.DoesNotExist:
            return Response({"error": "Device not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve all calculators
        response_all_calcs = requests.get(base_url_cal_check, headers=headers)
        if response_all_calcs.status_code != 200:
            return Response({"error": "Failed to retrieve all calculators from Flespi."}, status=response_all_calcs.status_code)

        all_calcs_data = response_all_calcs.json()
        matched_calculators = [
            calc for calc in all_calcs_data['result']
            if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
        ]

        # Create additional information dictionary
        new_geofence = {
            "center": center,
            "name": name,
            "radius": radius,
            "type": type_
        }
        additional_info = {
            "name": name,
            "alertOnEnter": alert_on_enter,
            "alertOnExit": alert_on_exit,
            "alertOnNotification": alert_on_notification
        }

        # Payload for creating a new geofence calculator
        payload = [{
            "intervals_ttl": 15550000,
            "update_delay": 30,
            "update_period": 604800,
            "update_onchange": True,
            "messages_source": {"source": "device"},
            "validate_message": "position.valid==true && device_status == 'Moving'",
            "validate_interval": "",
            "name": f"Geofences_IMEI_{IMEI}",
            "selectors": [{
                "geofences": [new_geofence],
                "type": "geofence",
                   "max_inactive": 30,
      "min_duration": 1
                
            }],
            "intervals_rotate": 0,
            "counters": [
                {"method": "first", "name": "position.latitude.in", "parameter": "position.latitude", "type": "parameter"},
                {"method": "first", "name": "position.longitude.in", "parameter": "position.longitude", "type": "parameter"},
                {"method": "last", "name": "position.latitude.out", "parameter": "position.latitude", "type": "parameter"},
                {"method": "last", "name": "position.longitude.out", "parameter": "position.longitude", "type": "parameter"},
                {"name": "geofence", "type": "geofence"},
                {"name": "alert", "type": "specified", "value": "geofence"},
                {"method": "first", "name": "ident", "type": "parameter"},
                {
                  "expression": "'Geofence Alert of '",
                  "method": "first",
                  "name": "notificationBody",
                  "type": "expression"
                },
                {
                  "expression": "'Geofence Alert'",
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
                      "name": "nickName",
                      "type": "parameter",
                      "parameter": "device.name"
                   }
                # {"name": "messages", "type": "specified", "value": json.dumps([additional_info])}  # Include additional_info in messages counter as an array of dictionaries
            ],
            "timezone": "America/Los_Angeles",
            "metadata": { "imei": str(IMEI)
            }
        }]

        if not matched_calculators:
            # If no matching calculator found, create a new one
            response_cal_creation = requests.post(url_cal_creation, headers=headers, json=payload)
            if response_cal_creation.status_code == 200:
                # Create GeofenceAlarms entry
                
                Geofence_exist=GeofenceAlarms.objects.filter(device_id=device_id,name=name).exists()
                if Geofence_exist:
                    return Response({"message":"Geofence with this name Already Exist","uniqueness":False},status=status.HTTP_400_BAD_REQUEST)
                GeofenceAlarms.objects.create(
                    device_id=device_id,
                    name=name,
                    longitude=center['lon'],
                    latitude=center['lat'],
                    radius=radius,
                    alertOnEnter=alert_on_enter,
                    alertOnExit=alert_on_exit,
                    alertOnNotification=alert_on_notification
                )
            return Response({"data": {
                "device_id":device_id,
                "name":name,
                "longitude":center['lon'],
                "latitude":center['lat'],
                "radius":radius,
                "alertOnEnter":alert_on_enter,
                "alertOnExit":alert_on_exit,
                "alertOnNotification":alert_on_notification
            }, "status": 200}, status=status.HTTP_200_OK)

        # If matching calculator found, update the existing one
        matched_calculator = matched_calculators[0]
        calc_selector = matched_calculator['id']
        allowed_properties = [
            "name", "messages_source", "update_period", "update_delay", "update_onchange",
            "intervals_ttl", "intervals_rotate", "selectors", "counters", "validate_interval",
            "validate_message", "timezone", "metadata"
        ]
        cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}

        # Update geofences and messages in the matched calculator
        if "selectors" in cleaned_calculator and len(cleaned_calculator["selectors"]) > 0:
            cleaned_calculator["selectors"][0]["geofences"].append(new_geofence)
        else:
            cleaned_calculator["selectors"] = [{"geofences": [new_geofence], "type": "geofence"}]

        # Update the messages counter
        # existing_messages = next((counter for counter in cleaned_calculator["counters"] if counter["name"] == "messages"), None)
        # if existing_messages:
        #     # Check if existing_messages["value"] is a string, and convert it to a list if necessary
        #     if isinstance(existing_messages["value"], str):
        #         existing_messages["value"] = json.loads(existing_messages["value"])
        #     existing_messages["value"].append(json.dumps(additional_info))
        #     existing_messages["value"] = json.dumps(existing_messages["value"])
        # else:
        #     cleaned_calculator["counters"].append({"name": "messages", "type": "specified", "value": [additional_info]})

        update_url = f"https://flespi.io/gw/calcs/{calc_selector}?fields=update_delay,update_period,update_onchange,validate_message,validate_interval,intervals_ttl,intervals_rotate,messages_source,metadata"
        response_update = requests.put(update_url, headers=headers, json=cleaned_calculator)

        if response_update.status_code == 200:
            Geofence_exist=GeofenceAlarms.objects.filter(device_id=device_id,name=name).exists()
            if Geofence_exist:
                    return Response({"message":"Geofence with this name Already Exist","uniqueness":False},status=status.HTTP_400_BAD_REQUEST)
            # Create GeofenceAlarms entry
            geofence=GeofenceAlarms.objects.create(
                device_id=device_id,
                name=name,
                longitude=center['lon'],
                latitude=center['lat'],
                radius=radius,
                alertOnEnter=alert_on_enter,
                alertOnExit=alert_on_exit,
                alertOnNotification=alert_on_notification
            )
            
        if response_update.status_code != 200:
            return Response({"error": "Failed to update calculator on Flespi.", "details": response_update.json()}, status=response_update.status_code)

        return Response({"data": {
                "id":geofence.id,
                "device_id":device_id,
                "name":name,
                 "center":{
                    "latitude": geofence.latitude,
                    "longitude": geofence.longitude,
                },
                "radius":radius,
                "alertOnEnter":alert_on_enter,
                "alertOnExit":alert_on_exit,
                "alertOnNotification":alert_on_notification
            }, "status": 200}, status=status.HTTP_200_OK)

    def delete(self, request, device_id):
        center1 = request.data.get('center', None)
        # print(type(center1))
        # print(center1)
        name = request.data.get('name', None)
        radius = float(request.data.get('radius', None))
        center={
        "lat": float(center1.pop('latitude')),
        "lon": float(center1.pop('longitude'))
        }
        # print(type(center))
        # print(center)

        if not all([center, name, radius]):
            return Response({"error": "center, name, radius are required.", "status": 400}, status=status.HTTP_400_BAD_REQUEST)

        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
        base_url_cal_check = f"https://flespi.io/gw/calcs/all"
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

        # Perform the GET request to retrieve device calculators
        response = requests.get(base_url_cal, headers=headers)
        if response.status_code != 200:
            return Response({"error": "Failed to retrieve data from Flespi."}, status=response.status_code)
        data = response.json()

        # Filter out the objects where auto_created is false
        filtered_data = [item for item in data['result'] if not item['auto_created']]
        filtered_calc_ids = [item['calc_id'] for item in filtered_data]

        # Retrieve the device's IMEI
        try:
            IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
            if not IMEI:
                return Response({"error": "IMEI not found for the given device ID."}, status=status.HTTP_404_NOT_FOUND)
        except Device.DoesNotExist:
            return Response({"error": "Device not found."}, status=status.HTTP_404_NOT_FOUND)

        # Perform the GET request to retrieve all calculators
        response_all_calcs = requests.get(base_url_cal_check, headers=headers)
        if response_all_calcs.status_code != 200:
            return Response({"error": "Failed to retrieve all calculators from Flespi."}, status=response_all_calcs.status_code)
        all_calcs_data = response_all_calcs.json()

        # Filter all calculators to include only those with calc_id in filtered_calc_ids and name containing IMEI
        matched_calculators = [
            calc for calc in all_calcs_data['result']
            if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
        ]

        if not matched_calculators:
            return Response({"error": "No matching calculator found."}, status=status.HTTP_404_NOT_FOUND)

        # Filter out the matching geofence from the selectors
        matched_calculator = matched_calculators[0]
        geofences = matched_calculator['selectors'][0]['geofences']
        print(geofences)
        updated_geofences = [g for g in geofences if not ( g['name'] == name)]
        # updated_geofences = [g for g in geofences if not (g['center'] == center and g['name'] == name and g['radius'] == radius)]

        # if len(geofences) == len(updated_geofences):
        #     return Response({"error": "No matching geofence found to delete."}, status=status.HTTP_404_NOT_FOUND)

        # If no geofences remain, delete the calculator
        if not updated_geofences:
            delete_url = f"https://flespi.io/gw/calcs/{matched_calculator['id']}"
            response_delete = requests.delete(delete_url, headers=headers)
            print(response_delete.json())
            if response_delete.status_code != 200:
                return Response({"error": "Failed to delete calculator on Flespi.", "details": response_delete.json()}, status=response_delete.status_code)
        else:
            matched_calculator['selectors'][0]['geofences'] = updated_geofences

            # Perform the PUT request to update the calculator on Flespi
            calc_selector = matched_calculator['id']
            allowed_properties = [
                "name", "messages_source", "update_period", "update_delay", "update_onchange",
                "intervals_ttl", "intervals_rotate", "selectors", "counters", "validate_interval",
                "validate_message", "timezone", "metadata"
            ]
            cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}
            update_url = f"https://flespi.io/gw/calcs/{calc_selector}?fields=update_delay,update_period,update_onchange,validate_message,validate_interval,intervals_ttl,intervals_rotate,messages_source,metadata"
            response_update = requests.put(update_url, headers=headers, json=cleaned_calculator)
            print("here")
            print(cleaned_calculator)

            if response_update.status_code != 200:
                return Response({"error": "Failed to update calculator on Flespi.", "details": response_update.json()}, status=response_update.status_code)

        # Delete GeofenceAlarms entry
        DeleteGeofence=GeofenceAlarms.objects.filter(
            device_id=device_id,
            name=name,
            # longitude=center['lon'],
            # latitude=center['lat'],
            # radius=radius
        ).delete()

        return Response({"data": {
                "device_id":device_id,
                "name":name,
                "longitude":center['lon'],
                "latitude":center['lat'],
                "radius":radius,
                # "alertOnEnter":DeleteGeofence.alert_on_enter,
                # "alertOnExit":DeleteGeofence.alert_on_exit,
                # "alertOnNotification":DeleteGeofence.alert_on_notification
            },"status": "Geofence deleted successfully."}, status=status.HTTP_200_OK)
    def patch(self, request, device_id):
        geofence_id = request.data.get('geofence_id')
        name = request.data.get('name')  # New name for the geofence
        updates = request.data.get('updates', {})  # Additional geofence updates

        # Validate request data
        if not geofence_id:
            return Response({"error": "Geofence ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        if name is None and not updates:
            return Response({"error": "Name or updates are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve geofence from the database
        try:
            geofence = GeofenceAlarms.objects.get(id=geofence_id, device_id=device_id)
        except GeofenceAlarms.DoesNotExist:
            return Response({"error": "Geofence not found for the given ID."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure name is not null; use the current name if not provided
        name = name or geofence.name
        name_changed = geofence.name != name

        # Check for unique geofence name for the device
        if name_changed:
            if GeofenceAlarms.objects.filter(device_id=device_id, name=name).exclude(id=geofence_id).exists():
                return Response({"error": "A geofence with this name already exists for this device."},
                                status=status.HTTP_400_BAD_REQUEST)

        # Retrieve calculators from Flespi
        base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
        headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
        response = requests.get(base_url_cal, headers=headers)

        if response.status_code != 200:
            return Response({"error": "Failed to retrieve data from Flespi."}, status=response.status_code)

        data = response.json()
        filtered_data = [item for item in data['result'] if not item['auto_created']]
        filtered_calc_ids = [item['calc_id'] for item in filtered_data]

        # Retrieve IMEI of the device
        IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
        if not IMEI:
            return Response({"error": "IMEI not found for the given device ID."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve all calculators
        response_all_calcs = requests.get("https://flespi.io/gw/calcs/all", headers=headers)
        if response_all_calcs.status_code != 200:
            return Response({"error": "Failed to retrieve all calculators from Flespi."}, status=response_all_calcs.status_code)

        all_calcs_data = response_all_calcs.json()
        matched_calculators = [
            calc for calc in all_calcs_data['result']
            if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
        ]

        if not matched_calculators:
            return Response({"error": "No matching calculator found."}, status=status.HTTP_404_NOT_FOUND)

        matched_calculator = matched_calculators[0]
        geofences = matched_calculator['selectors'][0]['geofences']

        # Update matching geofence in Flespi
        updated_geofences = []
        for g in geofences:
            if g['name'] == geofence.name:
                if name_changed:
                    g['name'] = name
                for key, value in updates.items():
                    if key in g:
                        g[key] = value
            updated_geofences.append(g)

        # If no geofences remain, delete the calculator
        if not updated_geofences:
            delete_url = f"https://flespi.io/gw/calcs/{matched_calculator['id']}"
            response_delete = requests.delete(delete_url, headers=headers)
            if response_delete.status_code != 200:
                return Response({"error": "Failed to delete calculator on Flespi.", "details": response_delete.json()},
                                status=response_delete.status_code)
            # Delete geofence from the database
            geofence.delete()
            return Response({"message": "Geofence and calculator deleted successfully."}, status=status.HTTP_200_OK)

        # Update geofences on Flespi
        matched_calculator['selectors'][0]['geofences'] = updated_geofences

        # Define allowed properties for updating a calculator
        allowed_properties = [
            "name", "messages_source", "update_period", "update_delay", "update_onchange",
            "intervals_ttl", "intervals_rotate", "selectors", "counters", "validate_interval",
            "validate_message", "timezone", "metadata"
        ]

        # Clean the calculator payload to only include allowed properties
        cleaned_calculator = {key: matched_calculator[key] for key in allowed_properties if key in matched_calculator}

        # Remove additional properties like 'cid' if present
        if "cid" in cleaned_calculator:
            del cleaned_calculator["cid"]

        # Send the updated payload to Flespi
        update_url = f"https://flespi.io/gw/calcs/{matched_calculator['id']}?fields=selectors"
        response_update = requests.put(update_url, headers=headers, json=cleaned_calculator)

        if response_update.status_code != 200:
            return Response({"error": "Failed to update calculator on Flespi.", "details": response_update.json()},
                            status=response_update.status_code)

        # Update the database
        if name_changed:
            geofence.name = name
        if "center" in updates:
            geofence.latitude = updates["center"].get("lat", geofence.latitude)
            geofence.longitude = updates["center"].get("lon", geofence.longitude)
        for key, value in updates.items():
            if key not in ["center"]:  # Skip center since it's handled separately
                setattr(geofence, key, value)
        geofence.save()

        return Response({
            "message": "Geofence updated successfully.",
            "data":{
                "id":geofence.id,
                "device_id":device_id,
                "name":geofence.name,
                "center":{
                    "latitude": geofence.latitude,
                    "longitude": geofence.longitude,
                },
                "radius":geofence.radius,
                "alertOnEnter":geofence.alertOnEnter,
                "alertOnExit":geofence.alertOnExit,
                "alertOnNotification":geofence.alertOnNotification
            }
        }, status=status.HTTP_200_OK)
