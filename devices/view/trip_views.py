from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
import requests
from devices.models import *
from devices.serializer import *
import json
from django.shortcuts import get_object_or_404
import datetime
import time
import calendar
from backend.utils import *
class TelemeryView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request,devSelector=None,temeletry=None):
       
        
        if str(devSelector).strip() == "all":
            UserDevices=UserSelectedDeviceSerializer(UserSelectedDevice.objects.filter(user=request.user),many=True)
            
            UserDevices=list(map(lambda device: str(device["device_id"]),UserDevices.data))
            UserDevices=','.join(UserDevices)
            response=requests.get(f"https://flespi.io/gw/devices/{UserDevices}/telemetry/{temeletry}", headers={"Authorization":"FlespiToken "+settings.FLESPI_TOKEN})
            response_data=response.json()
            result = response_data.get("result",[])
            return Response({"data":result,"status":200},status=HTTP_200_OK)
        response=requests.get(f"https://flespi.io/gw/devices/{devSelector}/telemetry/{temeletry}", headers={"Authorization":"FlespiToken "+settings.FLESPI_TOKEN})
        response_data=response.json()
        result = response_data.get("result",[])
        if "errors" in response_data:
            errors = response_data["errors"]
            return Response({"error": errors[0].get("reason"), "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
        return Response({"data":result,"status":200},status=HTTP_200_OK)

class TripsView(APIView):
  def get(self, request,day=None,month=None,deviceID=None):
        devSelector = deviceID
        date = day
        month_check = month
        month = month



        if not devSelector:
            return Response({"error": "Device selector (id) is required"}, status=status.HTTP_400_BAD_REQUEST)



        current_date = datetime.datetime.now().date()
        device=Device.objects.filter(device_id=devSelector).first()
        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_400_BAD_REQUEST)
        car = self.get_car_by_device_id(deviceID)
        car_alarms = car.CarAlarms
        cal_ids=[]
        
        if car_alarms.speedAlertEnabled:
            # urls["speed"] = f'https://flespi.io/gw/calcs/1703273/devices/{device_id}/intervals/all'
            if device.speedCalid:
                cal_ids.append(str(device.speedCalid))
        if car_alarms.harshBrakingAlertEnabled:
            # urls["harsh_brake"] = f'https://flespi.io/gw/calcs/1701359/devices/{device_id}/intervals/all'
            cal_ids.append('1701359')
        if car_alarms.hardBrakingAlertEnabled:
           
            if device.hardBrakingCalid:
                cal_ids.append(str(device.hardBrakingCalid))
        if car_alarms.ignitionStatusAlertEnabled:
            # urls["ignition_detection"] = f'https://flespi.io/gw/calcs/1702300/devices/{device_id}/intervals/all'
            cal_ids.append('1702300')
        if car_alarms.aggressiveSteeringAlertEnabled:
            # urls['collision_detection'] = f'https://flespi.io/gw/calcs/1701842/devices/{device_id}/intervals/all'
            cal_ids.append('1716456')
        if car_alarms.fuelAlertEnabled:
            # urls['fuel'] = f'https://flespi.io/gw/calcs/1700996/devices/{device_id}/intervals/all'
            if device.fuelCalid:
                cal_ids.append(str(device.fuelCalid))
        if car_alarms.batteryAlertEnabled:
            # urls['battery'] = f'https://flespi.io/gw/calcs/1703304/devices/{device_id}/intervals/all'
            if device.batteryCalid:
                cal_ids.append(str(device.batteryCalid))
        
        if car_alarms.tamperAlertAlertEnabled:
            # urls['temperAlert'] = f'https://flespi.io/gw/calcs/1709056/devices/{device_id}/intervals/all'
            cal_ids.append('1709056')
        if car_alarms.batteryVoltageAlertEnabled:
            # urls['batteryVoltage'] = f'https://flespi.io/gw/calcs/1709063/devices/{device_id}/intervals/all'
            cal_ids.append('1709063')
          
        



        url_alarms = f"https://flespi.io/gw/calcs/{','.join(cal_ids)}/devices/{devSelector}/intervals/all"
        if month:
            try:
                year, month = map(int, month.split('-'))
                _, last_day = calendar.monthrange(year, month)
                month_start = f"{year}-{month:02d}-01"
                month_end = f"{year}-{month:02d}-{last_day}"



                date_time_start = datetime.datetime.strptime(month_start + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
                date_time_end = datetime.datetime.strptime(month_end + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
                
                if date_time_end.date() > current_date:
                    date_time_end = datetime.datetime.combine(current_date, datetime.time.max)



                start_timestamp = int(time.mktime(date_time_start.timetuple()))
                end_timestamp = int(time.mktime(date_time_end.timetuple()))
        #    ://flespi.io/gw/calcs/1672521/devices/{devSelector}/intervals/all"
                url=f"https://flespi.io/gw/calcs/1712608/devices/{devSelector}/intervals/all"
                
                headers = {
                    "Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"
                } 
                params = {
                    "data": '{"begin":%d,"end":%d}' % (start_timestamp, end_timestamp)
                     
                }
                params_trip = {
                 "data": '{"filter":"trip_month=%d,trip_year=\\"%s\\""}' % (month, str(year))
                }




                try:
                    response = requests.get(url, headers=headers, params=params_trip)
                    response_alarms = requests.get(url_alarms, headers=headers, params=params)
                except requests.RequestException as e:
                    return Response({"error": f"Failed to fetch data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



                if response.status_code == 200:
                    
                    data=summarize_trips(response.json().get('result', []),response_alarms.json().get('result', []),device.speedThreshold)
                    monthly_report=data.pop()
                    
                    
                    date_str = month_check+'-01'
                    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    # Get the current date
                    current_date = datetime.datetime.now()
                    # Check if the year and month of the date match the current year and month
                    if date_obj.year == current_date.year and date_obj.month == current_date.month:
                        print("The date is in the current month.")
                        data=data[::-1]
                    else:
                        print("The date is not in the current month.")
                   
                    return Response({"monthlyReport":monthly_report,"monthlyTripsData":data, "status": 200}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": response.json().get("errors", "Failed to fetch trips data")}, status=response.status_code)
            except ValueError as e:
                return Response({"error": f"Invalid month format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        elif date:
            try:
                date_time_start = datetime.datetime.strptime(date + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
                date_time_end = datetime.datetime.strptime(date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')



                if date_time_end.date() > current_date:
                    date_time_end = datetime.datetime.combine(current_date, datetime.time.max)



                start_timestamp = int(time.mktime(date_time_start.timetuple()))
                end_timestamp = int(time.mktime(date_time_end.timetuple()))
                url = f"https://flespi.io/gw/calcs/1672521,1703304/devices/{devSelector}/intervals/all"
                headers = {
                    "Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"
                }
                params = {
                    "data": '{"begin":%d,"end":%d}' % (start_timestamp, end_timestamp)
                }



                try:
                    response = requests.get(url, headers=headers, params=params)
                except requests.RequestException as e:
                    return Response({"error": f"Failed to fetch data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



                if response.status_code == 200:
                    # data=response.json().get('result', [])
                    # data.pop()
                    trips_data = {"trips": response.json().get('result', [])}
                    return Response({"data": trips_data["trips"], "status": 200}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": response.json().get("errors", "Failed to fetch trips data")}, status=response.status_code)
            except ValueError as e:
                return Response({"error": f"Invalid date format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Either date or month is required"}, status=status.HTTP_400_BAD_REQUEST)

  def get_car_by_device_id(self,device_id):
            user_car_with_device = get_object_or_404(UserCarsWithDevice, device__device_id=device_id)
            return user_car_with_device.car



