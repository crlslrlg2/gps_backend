from django.conf import settings
import requests
from devices.models import Device
import datetime
import math
import boto3
from devices.models import *
from devices.serializer import *
from rest_framework.response import Response
def delete_s3_object(bucket_name, object_key):
    s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
    except Exception as e:
        print(f"Error deleting object {object_key} from bucket {bucket_name}: {e}")
def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula to calculate the great-circle distance between two points
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
def add_all_plugins(device_id):
    url = "https://flespi.io/gw/plugins/all"
    headers = {
        "Authorization": "FlespiToken V53GsvjsPV3GTliDBC67g8qgUU4evoFZUIOJXscgERbgMdlgqiARLZ9qBOT4ImLV"
    }    

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        plugins = response.json().get("result", [])
        plugin_ids = [str(plugin["id"]) for plugin in plugins]
        plugins_id_str = ','.join(plugin_ids)

        url_plugins = f"https://flespi.io/gw/plugins/{plugins_id_str}/devices/{device_id}"
        response_plugins = requests.post(url_plugins, headers=headers)

        if response_plugins.status_code == 200:
            print("All plugins added successfully")
        else:
            print(f"Failed to add all plugins: {response_plugins.status_code} - {response_plugins.text}")

    else:
        print(f"Failed to retrieve plugins: {response.status_code} - {response.text}")

def car_data_with_telemetry(id,telemetry):
    # user = UserCustomModel.objects.filter(email=request.user).first()
    print(telemetry)
    cars = Car.objects.filter(id=id)
    if cars.count() == 0:
        return Response({"data": [], "status": 200}, status=status.HTTP_200_OK)
    
    deviceIDs = UserCarsWithDevice.objects.filter(car__in=cars).values_list('device__device_id', flat=True)
    telemetry_dict = {}
    if deviceIDs.count() > 0:
        deviceIDs = ','.join(list(map(str, deviceIDs)))
        response = requests.get(
            f"https://flespi.io/gw/devices/{deviceIDs}/telemetry/{telemetry}" ,
            headers={"Authorization": "FlespiToken " + settings.FLESPI_TOKEN}
        )
        response_data = response.json()
        telemetry_data = response_data.get("result", [])
        print('here is a device')
        if "errors" in response_data:
            errors = response_data["errors"]
            return Response({"error": errors[0].get("reason"), "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a dictionary to quickly look up telemetry data by device ID
        telemetry_dict = {item['id']: item.get('telemetry') for item in telemetry_data}
    
    # Serialize car data
    serialized_cars = CarSerializer(cars, many=True).data
    
    # Combine car data with telemetry data
    combined_data = []
    for car in serialized_cars:
        device_id = car.get("deviceId")
        if device_id:
            car["telemetry"] = telemetry_dict.get(device_id, None)
        else:
            car["telemetry"] = None
        combined_data.append(car)
    return combined_data
def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])
def create_and_assign_calculator(devSelector, fuel_threshold):
    device=Device.objects.filter(device_id=devSelector).first()
    url_cal_creation = "https://flespi.io/gw/calcs"
    headers = {
        "Authorization": "FlespiToken V53GsvjsPV3GTliDBC67g8qgUU4evoFZUIOJXscgERbgMdlgqiARLZ9qBOT4ImLV",
        "Content-Type": "application/json"
    }
    
    payload = [{
        "intervals_ttl": 31536000,
        "update_delay": 1,
        "update_period": 604800,
        "update_onchange": True,
        "messages_source": {
            "source": "device"
        },
        "validate_message": "",
        "validate_interval": "",
        "name": "Fuel % alarm (Test)",
        "selectors": [
            {
                "expression": f"(can.remaining.fuel.level < {fuel_threshold})",
                "max_messages_time_diff": 604799,
                "merge_message_after": True,
                "merge_message_before": True,
                "merge_unknown": True,
                "method": "boolean",
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
            }
        ],
        "timezone": "UTC",
        "metadata": {
            "imei": str(86893506003814)
        }
    }]


    response = requests.post(url_cal_creation, headers=headers, json=payload)


    if response.status_code == 200:
        data = response.json()
        calculator_id = data['result'][0]['id']
        
        print("Calculator successfully created with ID:", calculator_id)
        device.fuelCalidation=calculator_id
        url_assign_calculator = f"https://flespi.io/gw/calcs/{calculator_id}/devices/{devSelector}"
        assign_response = requests.post(url_assign_calculator, headers=headers, json={})
        device.save()
        if assign_response.status_code == 200:
            print(f"Calculator {calculator_id} successfully assigned to device {devSelector}.")
            return True
        else:
            print(f"Failed to assign calculator to device. Status code: {assign_response.status_code}")
            print("Response:", assign_response.text)
            return False
    else:
        print(f"Failed to create calculator. Status code: {response.status_code}")
        print("Response:", response.text)
        return False
# Function to convert keys to camel case
def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])



def summarize_trips(trip_data, alarms,speed_threshold):

    summary = []
    month_total = {
        'totalTrips': 0,
        'totalDistance': 0.0,
        'totalDuration': datetime.timedelta(),
    }
   


    for trip in trip_data:
        date_str = datetime.datetime.utcfromtimestamp(trip['begin']).strftime('%Y-%m-%d')
        found_date = False


        for item in summary:
            if item['date'] == date_str:
                found_date = True
                break


        if not found_date:
            summary.append({
                'date': date_str,
                'day': str(date_str.split('-')[2]),
                'month': str(date_str.split('-')[1]),
                'year': str(date_str.split('-')[0]),
                'beginUtcStr': trip['begin-utc-str'],
                'endUtcStr': trip['end-utc-str'],
                'trips': [],
                'totalTrips': 0,
                'totalDistance': 0.0,
                'totalDuration': datetime.timedelta(),
                'trips': [],
                'alarms': []
            })


        trip_info = {
            to_camel_case(key): value for key, value in trip.items()
        }
        trip_info['alarms'] = []
        


        for point in trip_info['points']:
            date_format = '%Y-%m-%d %H:%M:%S'
            # point_alarms = [alarm for alarm in alarms if alarm['latitude'] == point['latitude'] and alarm['longitude'] == point['longitude'] ]
            point_event_time = datetime.datetime.strptime(point['event_time'], date_format)

            # Filter alarms to match latitude, longitude, and event_time up to the minute
            point_alarms = [
                alarm for alarm in alarms
                if (
                    (
                        # For speed alert, check full event_time including seconds
                        (alarm['alert'] == 'speed' and
                         datetime.datetime.strptime(alarm['event_time'], date_format) == point_event_time)
                        or
                        (alarm['alert'] == 'ignition_off' and
                         (alarm['longitude'] == point['longitude'] or alarm['latitude'] == point['latitude'])
                         and 
                         (datetime.datetime.strptime(alarm['event_time'], date_format).replace(second=0)-datetime.timedelta(minutes=1))== point_event_time.replace(second=0))
                        or
                        # For other alert types, check longitude and truncated event_time
                        (alarm['alert'] != 'speed' and alarm['alert']!='ignition_off' and
                         alarm['longitude'] == point['longitude'] and
                         datetime.datetime.strptime(alarm['event_time'], date_format).replace(second=0) == point_event_time.replace(second=0))
                    )
                )
            ]

            # point_alarms_speed = [alarm for alarm in alarms if alarm['latitude'] == point['latitude'] and alarm['longitude'] == point['longitude'] and alarm['alert']=='speed']
            [speed.update({'speed_limit': speed_threshold}) for speed in point_alarms if speed['alert'] == 'speed']

            if point_alarms:
                # print("point_alarms",point_alarms)
                point['alarms'] = point_alarms
                trip_info['alarms'].extend(point_alarms)
            else:
                point['alarms'] = []
              
            
      
        date_summary = next(item for item in summary if item['date'] == date_str)
        date_summary['totalTrips'] += 1
        date_summary['totalDistance'] += trip['distance']
        date_summary['totalDuration'] += datetime.timedelta(seconds=trip['duration'])
        date_summary['trips'].append(trip_info)
        # date_summary['alarms']=[]
        # date_summary['alarms'].extend(trip_info['alarms'].copy())
        # print("date_summary",date_summary['alarms'])


        # Update month totals
        month_total['totalTrips'] += 1
        month_total['totalDistance'] += trip['distance']
        month_total['totalDuration'] += datetime.timedelta(seconds=trip['duration'])


    # Convert timedelta to hours and minutes for each date
    for date_summary in summary:
        total_seconds = date_summary['totalDuration'].total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)


        if hours > 0:
            date_summary['totalDuration'] = f"{hours}h:{minutes}m"
        else:
            date_summary['totalDuration'] = f"{minutes}m"


        for trip in date_summary['trips']:
            trip_seconds = trip['duration']
            trip_hours = int(trip_seconds // 3600)
            trip_minutes = int((trip_seconds % 3600) // 60)


            if trip_hours > 0:
                trip['formattedDuration'] = f"{trip_hours}h:{trip_minutes}m"
            else:
                trip['formattedDuration'] = f"{trip_minutes}m"


        # Round total distance to one decimal place
        date_summary['totalDistance'] = round(date_summary['totalDistance'], 1)


        # Sort trips within each day in descending order of 'begin' timestamp
        date_summary['trips'] = sorted(date_summary['trips'], key=lambda x: x['begin'], reverse=True)


    # Convert timedelta to hours and minutes for the month total
    total_seconds = month_total['totalDuration'].total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)


    if hours > 0:
        month_total['totalDuration'] = f"{hours}h:{minutes}m"
    else:
        month_total['totalDuration'] = f"{minutes}m"


    # Round total distance to one decimal place
    month_total['totalDistance'] = round(month_total['totalDistance'], 1)


    # Add the month total to the summary
    summary.append({
        'totalTrips': month_total['totalTrips'],
        'totalDistance': month_total['totalDistance'],
        'totalDuration': month_total['totalDuration'],
    })


    return summary

      
def get_geofence_events( device_id,interval):
    headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
    events = []
    print(device_id)
    base_url_cal = f"https://flespi.io/gw/calcs/all/devices/{device_id}"
    response = requests.get(base_url_cal, headers=headers)
    
    data = response.json()
    filtered_data = [item for item in data.get('result', []) if not item.get('auto_created')]
    filtered_calc_ids = [item['calc_id'] for item in filtered_data]
    IMEI = Device.objects.filter(device_id=device_id).values_list('ident', flat=True).first()
    
    base_url_cal_check = "https://flespi.io/gw/calcs/all"
    response_all_calcs = requests.get(base_url_cal_check, headers=headers)
    
    all_calcs_data = response_all_calcs.json()
    matched_calculators = [
        calc for calc in all_calcs_data.get('result', [])
        if calc['id'] in filtered_calc_ids and str(IMEI) in calc['name']
    ]
   
    
    cal_id = matched_calculators[0]['id']
    geofence_data = matched_calculators[0]['selectors'][0]['geofences']
    geofence=""
    for geofences in geofence_data:
        if geofences['name']==interval.get('geofence'):
            geofence = geofences
            break
    
    geofence_center = (geofence['center']['lat'], geofence['center']['lon'])
    geofence_radius = geofence['radius'] * 1000
    
    lat_in = float(interval.get('position.latitude.in'))
    lon_in = float(interval.get('position.longitude.in'))
    lat_out = float(interval.get('position.latitude.out'))
    lon_out = float(interval.get('position.longitude.out'))

    distance_in = get_distance(lat_in, lon_in, geofence_center[0], geofence_center[1])
    distance_out = get_distance(lat_out, lon_out, geofence_center[0], geofence_center[1])
    
    inside_in = distance_in <= int(geofence_radius)
    inside_out = distance_out<= int(geofence_radius)
    
    event = ""
    # if inside_in and not inside_out:
    if int(distance_in) < int(distance_out) and inside_in :
        event = "exited"
    elif int(distance_in) > int(distance_out) and inside_out:
        event = "entered"
    
    return event