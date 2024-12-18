import time
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
from backend.utils import *
class DevicesTypes(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            # Fetch all channels
            channels_response = requests.get(
                "https://flespi.io/gw/channels/all",
                headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
            )
            channels_response.raise_for_status()
            channels_data = channels_response.json()

            # Check for errors in response
            if "errors" in channels_data:
                errors = channels_data["errors"]
                return Response({"error": errors[0].get("reason")}, status=HTTP_400_BAD_REQUEST)

            # Extract unique protocol IDs
            protocol_ids = {str(channel["protocol_id"]) for channel in channels_data["result"]}
            protocol_ids_str = ",".join(protocol_ids)

            # Fetch device types by protocol IDs
            device_types_response = requests.get(
                f"https://flespi.io/gw/channel-protocols/{protocol_ids_str}/device-types/all?fields=name,id,title",
                headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
            )
            device_types_response.raise_for_status()
            device_types_data = device_types_response.json()

            # Check for errors in response
            if "errors" in device_types_data:
                errors = device_types_data["errors"]
                return Response({"error": errors[0].get("reason")}, status=HTTP_400_BAD_REQUEST)

            return Response({"data": device_types_data["result"], "status": 200}, status=HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

class DeviceSelectedAfterCarCreatedView(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self,request,id=None):
        print(id)
        car=Car.objects.filter(id=id).first()
        if not car:
            return Response({"error":"Car not found","status":HTTP_400_BAD_REQUEST},status=HTTP_400_BAD_REQUEST)
        device = Device.objects.filter(ident=request.data["ident"]).first()
        if device:
            if device.status == "selected":
                return Response({"error": "Device already selected", "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
            user_device = UserSelectedDevice.objects.create(device_id=device, user=request.user)
            device.status = "selected"
            device.save()
            UserCarsWithDevice.objects.create(car=car, device=device)
            return Response({"data": "Device successfully created", "status": 200}, status=HTTP_200_OK)
        else:
            data = {
                "name": car.get("nickName"),
                "device_type_id": request.data.get("device_type_id",732),
                "configuration": {
                    "ident": request.data["ident"],
                    "settings_polling": "once"
                },
                "messages_rotate": 2048000,                          
            }
            response = requests.post("https://flespi.io/gw/devices", headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}, json=[data])
            response_data = response.json()
            if "errors" in response_data:
                errors = response_data["errors"]
                return Response({"error": errors[0].get("reason"), "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
            result = response_data.get("result")[0]
            device_serializer = DeviceSerializer(data={
                "device_id": result["id"],
                "device_type_id": result["device_type_id"],
                "ident": result["configuration"]["ident"],
                "status": "selected",
                "name": result["name"]
            })
            if device_serializer.is_valid():
                device = device_serializer.save()
                user_device = UserSelectedDevice.objects.create(device_id=device, user=request.user) 
                user_device.save()
                UserCarsWithDevice.objects.create(car=car, device=device)
                return Response({"data": "Device successfully created", "status": 200}, status=HTTP_200_OK)
            else:
                error_message=next(iter(device_serializer.errors.values()))[0]  
                return Response({"error": error_message, "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
                
class DeviceView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request,id=None):
        print(id)
        if str(id).strip() == "all":
            devices = Device.objects.all()
            serializer = DeviceSerializer(devices, many=True)
            print(request.user)
            return Response({"data":serializer.data,"status":200},status=HTTP_200_OK)
        else:
            UserDevices=UserSelectedDeviceSerializer(UserSelectedDevice.objects.filter(user=request.user),many=True)
            return Response({"data":UserDevices.data,"status":200},status=HTTP_200_OK)
            
    def post(self, request,id=None):
        response=requests.post("https://flespi.io/gw/devices", headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"},json=request.data)
        response_data=response.json()
        if "errors" in response_data:
            errors = response_data["errors"]
            return Response({"error": errors[0].get("reason"), "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
        result = response_data.get("result")[0]
        response_plugin = requests.post(f"https://flespi.io/gw/groups/3031/devices/{result["id"]}", headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"})
        print(response_plugin.json())
        serialize = DeviceSerializer(data={
            "device_id": result["id"],
            "device_type_id": result["device_type_id"],
            "ident": result["configuration"]["ident"],
            "status": "selected",
            "name": result["name"]
        })
        try:
            serialize.is_valid(raise_exception=True)
            if serialize.is_valid():
                serialize.save()
                device=Device.objects.get(device_id=result["id"])
                UserDevice=UserSelectedDevice.objects.create(device_id=device,user=request.user)
                UserDevice.save()
                return Response({"data":serialize.data,"status":200},status=HTTP_200_OK)
        except Exception as e:
            return Response({'error':json.dumps(e),'status':'400'}, status=HTTP_400_BAD_REQUEST)
        return Response({"data":response.json(),"status":HTTP_200_OK},status=HTTP_200_OK)
    def delete(self, request,id=None):
        response=requests.delete(f'https://flespi.io/gw/devices/{id}', headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"})
        response_data=response.json()
        if "errors" in response_data:
            errors = response_data["errors"]
            return Response({"error": errors[0].get("reason"), "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
        device = Device.objects.get(device_id=id)
        device.delete()
        return Response({"data":response_data,"status":HTTP_200_OK},status=HTTP_200_OK)
    
class CarView(APIView):
 
    def get(self, request,telemetry):
        print("user",request.user)
        user = UserCustomModel.objects.filter(email=request.user).first()
        cars = Car.objects.filter(user=user).order_by('priority')
        
        if cars.count() == 0:
            return Response({"data": [], "status": 200}, status=status.HTTP_200_OK)
        
        deviceIDs = UserCarsWithDevice.objects.filter(car__in=cars).values_list('device__device_id', flat=True)
        telemetry_dict = {}
        if deviceIDs.count() > 0:
            deviceIDs = ','.join(list(map(str, deviceIDs)))

            response = requests.get(
                f"https://flespi.io/gw/devices/{deviceIDs}/telemetry/{telemetry}",
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
        # print(combined_data)
        return Response({"data": combined_data, "status": 200}, status=status.HTTP_200_OK)

  
    # Working Fine
    def post(self, request, id=None):
        # Create a mutable dictionary from request.data
        data = {key: request.data.get(key) for key in request.data}
        # print(data)
        # Map deviceTypeId to device_type_id
        data["device_type_id"] = data.pop("deviceTypeId", None)
        # vehicle_image = data.get("vehicleImage")
        # print('before',vehicle_image)
        # if vehicle_image:
        #     compressed_image = compress_image(vehicle_image, 512)
        #     print(compressed_image)
        #     data["vehicleImage"] = compressed_image
            

        # print("Vehicle Image", data.get("vehicleImage"))
        vehicle_image = request.FILES.get("vehicleImage")
        print('Before compression:', vehicle_image)

        compressed_image=''
        # if vehicle_image:
        #     compressed_image = compress_image(vehicle_image, 512)
        #     print('Compressed Image:', compressed_image)
        #     data["VehicleImage"] = compressed_image
        #     # data["VehicleImage"] = compressed_image

        print("Vehicle Image in Data:", data.get("vehicleImage"))
        telemetry_data = data.pop("telemetrySelectors", None)
        user = UserCustomModel.objects.filter(email=request.user).first()
        cars = Car.objects.filter(user=user)
        data["priority"] = str(cars.count() + 1)

        if str(data.get("nickName")) == "":
            data["nickName"] = f'{str(data.get("make")).capitalize()} {str(data.get("model")).capitalize()} {str(data.get("year"))}'

        serialize = CarSerializer(data=data)
        # print(serialize)
        if serialize.is_valid():
            
            serialize.save(user=request.user)
            car = serialize.save()

            if data.get("ident"):
                device = Device.objects.filter(ident=data["ident"]).first()
                if device:
                    if device.status == "selected":
                        car.delete()
                        return Response({"error": "Device already selected", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                    user_device = UserSelectedDevice.objects.create(device_id=device, user=request.user)
                    device.status = "selected"
                    device.save()
                    UserCarsWithDevice.objects.create(car=car, device=device)
                    if data.get("nickName",None):
                        data_values = {
                            "name": data.get("nickName")
                            }
                        requests.patch(f'https://flespi.io/gw/devices/{device.device_id}',headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"},json=data_values)

                    data = car_data_with_telemetry(car.id, telemetry_data)
                    return Response({"data": data[0], "message": "Vehicle and Car Created Successfully", "status": 200}, status=status.HTTP_200_OK)
                else:
                    if data.get("nickName"):
                        Name = str(data.get("nickName")).capitalize()
                    else:
                        Name = f'{str(data.get("make")).capitalize()} {str(data.get("model")).capitalize()} {str(data.get("year"))}'

                    device_data = {
                        "name": Name,
                        "device_type_id": int(data.get("device_type_id", 732)),
                        "configuration": {
                            "ident": data["ident"],
                            "settings_polling": "once"
                        },
                        "messages_rotate": 2048000
                    }
                    response = requests.post(
                        "https://flespi.io/gw/devices",
                        headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"},
                        json=[device_data]
                    )
                    response_data = response.json()
                    if "errors" in response_data:
                        errors = response_data["errors"]
                        car.delete()
                        error_message = errors[0].get("reason")
                        if error_message == "expecting ident to be an IMEI number (15 digits)":
                            error_message = "Device IMEI must be 15 Digits"
                        return Response({"error": error_message, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

                    result = response_data.get("result")[0]
                    response_plugin = requests.post(
                        f"https://flespi.io/gw/groups/3031/devices/{result['id']}",
                        headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
                    )
                    add_all_plugins(result["id"])

                    device_serializer = DeviceSerializer(data={
                        "device_id": result["id"],
                        "device_type_id": result["device_type_id"],
                        "ident": result["configuration"]["ident"],
                        "status": "selected",
                        "name": result["name"]
                    })
                    if device_serializer.is_valid():
                        device = device_serializer.save()
                        user_device = UserSelectedDevice.objects.create(device_id=device, user=request.user)
                        UserCarsWithDevice.objects.create(car=car, device=device)
                        data = car_data_with_telemetry(car.id, telemetry_data)
                        # if data.get("nickName",None):
                        #     data = {
                        #         "name": data.get("nickName")
                        #         }
                        #     requests.patch(f'https://flespi.io/gw/devices/{device.device_id}',headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"},json=data)
          
                        return Response({"data": data[0], "message": "Vehicle and Car Created Successfully", "status": 200}, status=status.HTTP_200_OK)
                    else:
                        car.delete()
                        error_message = next(iter(device_serializer.errors.values()))[0]
                        return Response({"error": error_message, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

            car_obj = serialize.data
            car_obj["telemetry"] = 'null'
            return Response({"data": car_obj, 'message': 'Car Successfully Created', "status": 200}, status=status.HTTP_200_OK)
        else:
            error_message = next(iter(serialize.errors.values()))[0]
            return Response({"error": error_message, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
   
    
    def patch(self, request, id=None):
        print("user", request.user)
        # Create a mutable dictionary from request.data and map deviceTypeId to device_type_id
        data = {key: request.data.get(key) for key in request.data}
        if "deviceTypeId" in data:
            data["device_type_id"] = data.pop("deviceTypeId")
        # Find the car by ID
        car = Car.objects.filter(id=id).first()
        carWithVehicle=UserCarsWithDevice.objects.filter(car=car.id).first()
        print("carWithVehicle",car.vehicleImage)
        print("herer")
        if "vehicleImage"  in data:
            if str(car.vehicleImage) !='vehicle_images/black-car-vector.png':  # Assuming `vehicle_image` field stores the S3 key
                delete_s3_object(settings.AWS_STORAGE_BUCKET_NAME, str(car.vehicleImage))
                # return Response({"success": True})     
        # return Response({"success": False})     
        if "ident" in data and "device_type_id" in data:
            if carWithVehicle:
                deviceId = carWithVehicle.device.device_id
                device = Device.objects.get(device_id=deviceId)
                device.status='unselected'
                device.save()
                carWithVehicle.device=None
                # response=requests.patch(f'https://flespi.io/gw/devices/{deviceId}', headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"})
                # response=requests.delete(f'https://flespi.io/gw/devices/{deviceId}', headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"})
                # response_data=response.json()
                # if "errors" in response_data:
                #     errors = response_data["errors"]
                #     return Response({"error": errors[0].get("reason"), "status": HTTP_400_BAD_REQUEST}, status=HTTP_400_BAD_REQUEST)
                # device.delete()
            
        

        if not car:
            return Response({"error": "Car not found", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # Update car data using serializer
  
        serializer = CarSerializer(car, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # Handle device association if 'ident' is provided
            ident = data.get("ident")
            if ident:
                device = Device.objects.filter(ident=ident).first()
                if device:
                    if device.status == "selected":
                        return Response({"error": "Device already selected", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

                    device.status = "selected"
                    device.save()
                    UserSelectedDevice.objects.create(device_id=device, user=request.user)
                    UserCarsWithDevice.objects.update_or_create(car=car, defaults={"device": device})
                else:
                    device_data = {
                        "name": car.nickName,
                        "device_type_id": int(data.get("device_type_id", 732)),
                        "configuration": {"ident": ident, "settings_polling": "once"},
                        "messages_rotate": 2048000,
                    }
                    response = requests.post("https://flespi.io/gw/devices", headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}, json=[device_data])
                    response_data = response.json()
                    if "errors" in response_data:
                        errors = response_data["errors"]
                        return Response({"error": errors[0].get("reason"), "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

                    result = response_data["result"][0]
                    device_serializer = DeviceSerializer(data={
                        "device_id": result["id"],
                        "device_type_id": result["device_type_id"],
                        "ident": result["configuration"]["ident"],
                        "status": "selected",
                        "name": result["name"]
                    })
                    if device_serializer.is_valid():
                        device = device_serializer.save()
                        UserSelectedDevice.objects.create(device_id=device, user=request.user)
                        UserCarsWithDevice.objects.update_or_create(car=car, defaults={"device": device})
                    else:
                        error_message = next(iter(device_serializer.errors.values()))[0]
                        return Response({"error": error_message, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

            if data.get("nickName",None):
                data = {
                    "name": data.get("nickName")
                    }
                requests.patch(f'https://flespi.io/gw/devices/{carWithVehicle.device.device_id}',headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"},json=data)
          
            return Response({"data": serializer.data, "message": "Car updated successfully", "status": 200}, status=status.HTTP_200_OK)
        else:
            error_message = next(iter(serializer.errors.values()))[0]
            return Response({"error": error_message, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
      
    def delete(self, request, id=None):
        try:
            car = Car.objects.get(id=id)

            # Serialize the car object before deletion
            carObj = CarSerializer(car)
            print(carObj.data)
            CarDevices = UserCarsWithDevice.objects.filter(car_id=car.id)
            if len(CarDevices) > 0:
                if car.car_selected_by_user.device:
                    print("here")
                    device_id = car.car_selected_by_user.device.device_id
                    device = Device.objects.get(device_id=device_id)
                    device.status = "unselected"
                    device.save()
                    CarDevice = UserSelectedDevice.objects.get(device_id=device_id)  
                    CarDevice.delete()
                    print(CarDevice)

            car.delete()

            return Response({"data": carObj.data, "message": "Car deleted successfully", "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)
        except:
            return Response({"error":"Car not found","status":HTTP_400_BAD_REQUEST},status=HTTP_400_BAD_REQUEST)

class getTelemetry(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request,telemetry,deviceIDs=None):
        
        if not deviceIDs:
            return Response({"error": "Device IDs are required", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        response = requests.get(
                f"https://flespi.io/gw/devices/{deviceIDs}/telemetry/{telemetry}",
                headers={"Authorization": "FlespiToken " + settings.FLESPI_TOKEN}
            )
        response_data = response.json()
        telemetry_data = response_data.get("result", [])
        # print('here is a device')
        if "errors" in response_data:
            errors = response_data["errors"]
            return Response({"error": errors[0].get("reason"), "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a dictionary to quickly look up telemetry data by device ID
        
        return Response({"data": telemetry_data, "status": 200}, status=status.HTTP_200_OK)
        
        
        

class VechicleSorters(APIView):
    authentication_classes = [JWTAuthentication]

    def patch(self, request):
        data = request.data.get('data', [])
        device_ids = [{i: ''.join(vehicle.get('id').split('-'))} for i, vehicle in zip(range(1, len(data) + 1), data)]
        
        # Update car priorities
        for id_dict in device_ids:
            for priority, car_id in id_dict.items():
                car = Car.objects.filter(id=car_id).first()
                if car:
                    car.priority = priority
                    car.save()
        cars = Car.objects.filter(user=request.user).order_by('priority')
        carSerializer = CarSerializer(cars, many=True)

        return Response({
            "data": carSerializer.data,
            "status": 200,
           
        }, status=status.HTTP_200_OK)

class GetSingleVehicle(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self,request,telemetry=None,id=None):
        
        cars = Car.objects.filter(id=id)
        
        if cars.count() == 0:
            return Response({"data": [], "status": 200}, status=status.HTTP_200_OK)
        
        deviceIDs = UserCarsWithDevice.objects.filter(car__in=cars).values_list('device__device_id', flat=True)
        telemetry_dict = {}
        if deviceIDs.count() > 0:
            deviceIDs = ','.join(list(map(str, deviceIDs)))

            response = requests.get(
                f"https://flespi.io/gw/devices/{deviceIDs}/telemetry/{telemetry}",
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
        
        return Response({"data": combined_data, "status": 200}, status=status.HTTP_200_OK)
   
class UpdateCarAlarms(APIView):
    permission_classes = [AllowAny]

    def put(self, request):
        try:
            # Retrieve the car_id from query parameters if provided
            car_id = self.request.query_params.get("id")
            if car_id is not None:
                # Log the car_id received
                print(f"Received car_id: {car_id}")
                
                # Filter the Car objects based on car_id
                queryset = Car.objects.all()
                car = queryset.filter(id=car_id).first()
                if car is None:
                    return Response({"error": "Car with provided car_id not found"}, status=status.HTTP_404_NOT_FOUND)
                
                # Log the Car object retrieved by car_id
                print(f"Car object by car_id: {car}")
                print(f"Car alarms by car_id: {car.CarAlarms}")

                # Access the CarAlarms related to car
                car_alarms = car.CarAlarms
                if car_alarms is None:
                    return Response({"error": "Car alarms not found."}, status=status.HTTP_404_NOT_FOUND)
                
                # Log the CarAlarms object
                print(f"Car alarms: {car_alarms}")
                print(f"collison alarm: {car_alarms.collisionDetectionAlarms}")

                # Serializer part (uncomment if needed)
                serializer = CarAlarmSerializer(car_alarms, data=request.data)
                if serializer.is_valid():
                     serializer.save()
                     return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # For now, return a success response to indicate the alarms were found
                #return Response({"message": "Car alarms retrieved successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "car_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
from datetime import  timedelta
import datetime

class DrivingStats(APIView):
    # permission_classes = [AllowAny]
    
    def get(self, request, device_id=None):
        if device_id is None:
            return Response({"error": "Device ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the query parameters for filtering
        filter_by = request.query_params.get('filter_by', None)  # e.g., last_30_days, last_7_days, etc.
        start_date_param = request.query_params.get('start_date', None)  # Custom start date (optional)
        end_date_param = request.query_params.get('end_date', None)  # Custom end date (optional)
        group_by = request.query_params.get('group_by', 'trip')  # e.g., trip, day, week

        # Initialize end_date as current UTC time
        end_date = datetime.datetime.utcnow()

        # Check for custom date range
        if start_date_param and end_date_param:
            try:
                start_date = datetime.datetime.strptime(start_date_param, '%Y-%m-%d')
                end_date = datetime.datetime.strptime(end_date_param, '%Y-%m-%d')
            except ValueError:
                return Response({"error": "Invalid date format, expected YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
        elif filter_by:  # Apply predefined filters if custom dates are not provided
            if filter_by == 'last_7_days':
                start_date = end_date - timedelta(days=7)
            elif filter_by == 'last_30_days':
                start_date = end_date - timedelta(days=30)
            elif filter_by == 'last_60_days':
                start_date = end_date - timedelta(days=60)
            elif filter_by == 'last_90_days':
                start_date = end_date - timedelta(days=90)
            elif filter_by == 'all_days':
                start_date = datetime.datetime(1970, 1, 1)  # Start of the Unix epoch
            else:
                return Response({"error": "Invalid filter provided"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Filter or date range is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Adjust end date if it exceeds the current date
        current_date = datetime.datetime.utcnow()
        if end_date.date() > current_date.date():
            end_date = current_date

        # Format start and end dates to timestamps for API request
        start_timestamp = int(time.mktime(start_date.timetuple()))
        end_timestamp = int(time.mktime(end_date.timetuple()))
        print("start_timestamp: %d, end_timestamp: %d" % (start_timestamp, end_timestamp))

        # Construct the URL
        url = f"https://flespi.io/gw/calcs/1712608/devices/{str(device_id)}/intervals/all"
        
        headers = {
            "Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"
        }
        params = {
            "data": '{"begin":%d,"end":%d}' % (start_timestamp, end_timestamp)
        }

        # Make the request to the Flespi API
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises HTTPError for bad requests
            data = response.json()
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Check for errors in the response
        if "errors" in data:
            errors = data["errors"][0].get("reason")
            return Response({"error": errors, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # Return filtered and grouped data
        total_trips = len(data['result'])
        total_idle_time = 0
        total_distance = 0
        total_duration = 0
        average_speed = 0
        average_overall_speed = 0
        max_speed = 0

        for trip in data['result']:
            total_idle_time += trip.get('idle_time', 0) if trip['idle_time'] is not None else 0
            total_distance += trip.get('distance', 0)  # Handle missing distance
            average_speed += trip.get("avg.moving.speed", 0)
            total_duration += trip.get('duration', 0)
            max_speed = max(max_speed, trip.get("max.speed", 0))


        average_speed = average_speed / total_trips if total_trips > 0 else 0
        average_speed = int(round(average_speed, 0))
        total_distance = int(round(total_distance, 0))
        average_overall_speed = total_distance / (total_duration / 3600) if total_duration > 0 else 0

        return Response({
            "data": {
                "total_trips": total_trips,
                "total_idle_time": total_idle_time,
                "mileage": total_distance,
                "total_duration": total_duration,
                "avg.moving.speed": average_speed,
                "max.speed": max_speed,
                "avg.overall.speed": average_overall_speed,
                "device_id": device_id
            },
            "message": "Data Successfully Retrieved",
            "status": status.HTTP_200_OK
        }, status=status.HTTP_200_OK)

class GetDeviceDetails(APIView):
    def get(self, request, device_id):
        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        device_details= Device.objects.filter(device_id=device_id).first()
        device_name=DeviceTypeId.objects.filter(deviceTypeId=device_details.device_type_id).first()
        try:
            # Fetch all channels
            channels_response = requests.get(
                "https://flespi.io/gw/channels/all",
                headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
            )
            channels_response.raise_for_status()
            channels_data = channels_response.json()

            # Check for errors in response
            if "errors" in channels_data:
                errors = channels_data["errors"]
                return Response({"error": errors[0].get("reason")}, status=HTTP_400_BAD_REQUEST)

            # Extract unique protocol IDs
            protocol_ids = {str(channel["protocol_id"]) for channel in channels_data["result"]}
            protocol_ids_str = ",".join(protocol_ids)

            # Fetch device types by protocol IDs
            device_types_response = requests.get(
                f"https://flespi.io/gw/channel-protocols/{protocol_ids_str}/device-types/{device_details.device_type_id}?fields=name,id,title",
                headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
            )
            device_types_response.raise_for_status()
            device_types_data = device_types_response.json()

            # Check for errors in response
            if "errors" in device_types_data:
                errors = device_types_data["errors"]
                return Response({"error": errors[0].get("reason")}, status=HTTP_400_BAD_REQUEST)
            device_types_data["result"][0]['ident']= str(device_details.ident)
            if device_name:
                device_types_data["result"][0]['deviceName']= str(device_name.deviceName)
            else:
                device_types_data["result"][0]['deviceName']= "No Data Exist "
            if device_types_data["result"][0]['name'] == 'tk418_s':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/EelinkTK418-S.png"
            elif device_types_data["result"][0]['name']=='jm_vl502':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-VL502.png"
            elif device_types_data["result"][0]['name']=='jm_ll04':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-VL04.png"
            elif device_types_data["result"][0]['name']=='jm_ll02':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-LL02.png"      
            elif device_types_data["result"][0]['name']=='jm_ll01':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-LL01.png"
            elif device_types_data["result"][0]['name']=='gt06n':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-GT06N.png"
            elif device_types_data["result"][0]['name']=='gf60l':
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-GF60L.png"
            else:
                device_types_data["result"][0]['deviceImage']="https://test-bucket-flespi.s3.us-east-2.amazonaws.com/Devices/JM-VL502.png"   
            return Response({"data": device_types_data["result"], "status": 200}, status=HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)



class DeviceCommand(APIView):

    def post(self, request, device_id):
        if not device_id:
            return Response({"error": "Device ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve command and other data from the request
            command = request.data.get('batteryMode')
            power_saving_mode_enabled = request.data.get('powerSavingModeEnabled')
            
            # Check if 'powerModeType' is present, convert to integer if exists
            if request.data.get('powerModeType'):
                print("Power Mode Type")
                command = int(request.data.get('powerModeType'))

            command_value = command

            # Ensure command is provided
            # if not command:
            #     return Response({"error": "Command is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate command - ensuring it's one of the accepted values
            if command not in ["active", "trip", "endurance", 1, 6, 12] and command:
                return Response({"error": "Invalid command."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if the device exists
            device = Device.objects.filter(device_id=device_id).first()
            if not device:
                return Response({"error": "Device not found."}, status=status.HTTP_404_NOT_FOUND)

            # Handle commands based on device type
            if device.device_type_id == 2309:
                if power_saving_mode_enabled:
                    # print("Power Saving Mode")
                    command = "MODE,1,10,0#"
                else:
                    # print("Power Mode Type")
                    command = f"MODE,2,{command_value}:00,24#"
            elif device.device_type_id == 2369:
                if command == 'active':
                    command = "md123456 0"
                elif command == 'trip':
                    command = "md123456 1 3 8 1"
                elif command == "endurance":
                    command = "md123456 3 3 (120)"
            else:
                return Response({"error": "Invalid device type."}, status=status.HTTP_400_BAD_REQUEST)

            # Prepare the flespi API request
            flespi_url = f'https://flespi.io/gw/devices/{device_id}/commands'
            headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
            data = [{"name": "custom", "properties": {"payload": command}}]

            # Send the request to flespi
            response = requests.post(flespi_url, headers=headers, json=data)
            response_data = response.json()

            # Handle possible errors in the flespi response
            if "errors" in response_data:
                errors = response_data["errors"]
                return Response({"error": errors[0].get("reason"), "active": False}, status=status.HTTP_400_BAD_REQUEST)

            # Update device state based on the command type
            if command_value in [1, 6, 12]:
                if power_saving_mode_enabled is not None:
                    device.powerSavingModeEnabled = power_saving_mode_enabled
                device.powerModeType = str(command_value)
            else:
                device.batteryMode = command_value

            # Save the device state
            device.save()

            # Successful response
            return Response({"message": "Command sent successfully", "active": True, "status": 200}, status=status.HTTP_200_OK)

        except Exception as e:
            # Handle any unexpected exceptions
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class DeviceTypeIdView(APIView):
 
    def get(self, request):
        devices = DeviceTypeId.objects.all()
        serializer = DeviceTypeIdSerializer(devices, many=True)
        return Response({"success":True,"data":serializer.data,"message":"Device Type ID Successfully Get"}, status=status.HTTP_200_OK)

   
    def post(self, request):
        serializer = DeviceTypeIdSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success":True,"data":serializer.data,"message":"Device Type ID Successfully Created"}, status=status.HTTP_201_CREATED)
        return Response({"success":False,"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    def patch(self, request, pk):
        try:
            device = DeviceTypeId.objects.get(deviceTypeId=pk)
        except DeviceTypeId.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = DeviceTypeIdSerializer(device, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success":True,"data":serializer.data,"message":"Device Type ID Successfully Updated"}, status=status.HTTP_200_OK)
        return Response({"success":False,"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            device = DeviceTypeId.objects.get(deviceTypeId=pk)
        except DeviceTypeId.DoesNotExist:
            return Response({"success":False,"error":"Device Type Id not Found"},status=status.HTTP_404_NOT_FOUND)

        device.delete()
        return Response({"success":True,"data":{"id":pk},"message":"Device Type ID Successfully Deleted"},status=status.HTTP_200_OK)
            