import re
from django.core.exceptions import ValidationError
from rest_framework import serializers
from auth_app.models import UserCustomModel
from devices.models import *
from .models import *
from django.db import transaction
from devices.serializer import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCustomModel
        fields = ['id', 'email', 'first_name', 'last_name', 'password','role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['email'] = validated_data['email'].lower()
        user = UserCustomModel.objects.filter(email=validated_data['email'])
        if user.exists():
            raise ValidationError("Email already exists")
        if 'password' in validated_data:
            user = UserCustomModel.objects.create_user(**validated_data)
        else:
            user = UserCustomModel.objects.create(**validated_data)
        return user

    def validate(self, validated_data):
        if validated_data.get('accountType') == 'default':
            password = validated_data.get('password', '')
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Z]', password):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password):
                raise ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'[0-9]', password):
                raise ValidationError("Password must contain at least one digit.")
            if not re.search(r'[!@#$%^&*()_+{}|:"<>?]', password):
                raise ValidationError("Password must contain at least one special character.")
        return validated_data





class DeviceInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceInventory
        fields = ['id', 'imei', 'sim_card', 'iccid', 'received_date', 'shipped_date', 'status','batch']
        read_only_fields = ['id']
class DeviceBatchUploadSerializer(serializers.ModelSerializer):
    devices = serializers.SerializerMethodField()
    # assign_to = serializers.SerializerMethodField()

    class Meta:
        model = DeviceBatchUpload
        fields = ['id', 'uploaded_file', 'batch_number', 'uploaded_at', 'created_by', 'devices','status']
        read_only_fields = ['id', 'uploaded_at', 'created_by']

    def get_devices(self, obj):
        # Retrieve related devices using the related_name defined in the model
        devices = DeviceInventory.objects.filter(batch=obj)  # `batch` is the related_name in DeviceInventory
        # Serialize the devices
        return DeviceInventorySerializer(devices, many=True).data

class VehicleAndDeviceCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    password = serializers.CharField(max_length=255)
    email = serializers.EmailField()  # This is the buyer's email
    vin = serializers.CharField(max_length=17)
    license_plate = serializers.CharField(required=False, allow_blank=True)
    model = serializers.CharField(max_length=255)
    year = serializers.IntegerField()
    make = serializers.CharField(max_length=255)
    ident = serializers.CharField(max_length=255)
    serial_number = serializers.CharField(required=False, allow_blank=True)
    vehicle_price = serializers.FloatField(required=False)
    device_price = serializers.FloatField(required=False)
    device_type_id = serializers.IntegerField(required=False)
    device_id = serializers.IntegerField(required=False)

    def validate(self, data):
        # Fetch the buyer or create a new user if not existing
        buyer = UserCustomModel.objects.filter(email=data.get('email')).first()
        if not buyer:
            buyer = UserCustomModel.objects.create_user(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                password=data['password']
            )
        data['buyer'] = buyer

        # Get the seller from the request context (authenticated user)
        request = self.context.get('request')
        seller = request.user

        # Check the seller's role
        if seller.role in ['department_user', 'finance_manager']:
            # Find the parent dealer (creator) of the seller
            parent = UserCreationLog.objects.filter(created_user=seller).first()
            if not parent:
                raise serializers.ValidationError("No parent user found for this seller.")

            # Fetch batches assigned to the parent dealer
            dealer_batches = DeviceBatchAssignment.objects.filter(assigned_to=parent.creator).values_list('batch', flat=True)

            # Check if the device is in the parent dealer's inventory
            device = DeviceInventory.objects.filter(imei=data['ident'], batch__in=dealer_batches).first()
            if not device:
                raise serializers.ValidationError(f"Device with IMEI {data['ident']} is not available in the assigned dealer's inventory.")
            
            # Check if the device is already in use
            print("device",data['ident'])
            device=Device.objects.filter(ident=data['ident']).first()
            print("device",device.status)
            if device.status != 'unselected':
                raise serializers.ValidationError(f"Device with IMEI {data['ident']} is already in use.")
            
            data['device'] = device

        elif seller.role != 'safelink':
            # For other roles except `safelink`, check their assigned batches
            seller_batches = DeviceBatchAssignment.objects.filter(assigned_to=seller).values_list('batch', flat=True)
            device = DeviceInventory.objects.filter(imei=data['ident'], batch__in=seller_batches).first()

            if not device:
                raise serializers.ValidationError(f"Device with IMEI {data['ident']} is not available in the seller's inventory.")
            
            print("device",data['ident'])
            device=Device.objects.filter(ident=data['ident']).first()
            print("device",device.status)
            if device.status != 'unselected':
                raise serializers.ValidationError(f"Device with IMEI {data['ident']} is already in use.")
            
            data['device'] = device

        # No restrictions for 'safelink' role
        elif seller.role == 'safelink':
            device = DeviceInventory.objects.filter(imei=data['ident']).first()
            if not device:
                raise serializers.ValidationError(f"Device with IMEI {data['ident']} does not exist in the inventory.")
            print("device",data['ident'])
            device=Device.objects.filter(ident=data['ident']).first()
            print("device",device.status)
            if device.status != 'unselected':
                raise serializers.ValidationError(f"Device with IMEI {data['ident']} is already in use.")
            
            
            data['device'] = device

        # Validate vehicle by VIN
        vehicle = Car.objects.filter(vinNumber=data['vin']).first()
        if vehicle:
            data['vehicle'] = vehicle

        return data
    # @transaction.atomic 
    def create(self, validated_data):
        # Get the seller from the request context
        request = self.context.get('request')
        seller = request.user
        buyer = validated_data['buyer']

        # Check if a vehicle exists, otherwise create one
        vehicle = validated_data.get('vehicle')
        if not vehicle:
            car_data = {
                'vinNumber': validated_data['vin'],
                'model': validated_data['model'],
                'year': validated_data['year'],
                'make': validated_data['make'],
                'price': validated_data.get('vehicle_price'),
                'user': buyer  # Vehicle is registered to the buyer
            }
            car_serializer = CarSerializer(data=car_data)
            car_serializer.is_valid(raise_exception=True)
            vehicle = car_serializer.save()

        # Ensure the vehicle is saved
        if not vehicle.pk:
            vehicle.save()

        # Check if a device exists, otherwise create one
        device = validated_data.get('device')
        if not device:
            device_data = {
                'ident': validated_data['ident'],
                'name': validated_data['ident'],
                'status': 'unselected',
                'device_type_id': validated_data.get('device_type_id'),
                'device_id': validated_data.get('device_id'),
                'price': validated_data.get('device_price')
            }
            device_serializer = DeviceSerializer(data=device_data)
            device_serializer.is_valid(raise_exception=True)
            device = device_serializer.save()
        else:
            # Update existing device
            device.status = 'selected'
            device.save()

        # Create a new DeviceVehicleSale record to track the sale
        DeviceVehicleSale.objects.create(
            seller=seller,
            buyer=buyer,
            device=device,
            vehicle=vehicle
        )

        return {
            "seller": seller,
            "buyer": buyer,
            "vehicle": vehicle,
            "device": device
        }
# class VehicleAndDeviceCreateSerializer(serializers.Serializer):
#     first_name = serializers.CharField()
#     last_name = serializers.CharField()
#     phone_number = serializers.CharField()
#     password = serializers.CharField(max_length=255)
#     email = serializers.EmailField()
#     vin = serializers.CharField(max_length=17)
#     license_plate = serializers.CharField(required=False, allow_blank=True)
#     model = serializers.CharField(max_length=255)
#     year = serializers.IntegerField()
#     make = serializers.CharField(max_length=255)
#     ident = serializers.CharField(max_length=255)
#     serial_number = serializers.CharField(required=False, allow_blank=True)
#     vehicle_price = serializers.FloatField(required=False)
#     device_price = serializers.FloatField(required=False)
#     device_type_id = serializers.IntegerField(required=False)
#     device_id = serializers.IntegerField(required=False)

#     # def validate(self, data):
#     #     # Check if the user exists or not
#     #     user = UserCustomModel.objects.filter(email=data['email']).first()
#     #     if not user:
#     #         user = UserCustomModel.objects.create_user(
#     #             first_name=data['first_name'],
#     #             last_name=data['last_name'],
#     #             email=data['email'],
#     #             password=data['password']
#     #         )
#     #     data['user'] = user

#     #     # Check for existing vehicle by VIN
#     #     vehicle = Car.objects.filter(vinNumber=data['vin']).first()
#     #     if vehicle:
#     #         data['vehicle'] = vehicle

#     #     # Check for existing device by IMEI (using ident)
#     #     device = Device.objects.filter(ident=data['ident']).first()
#     #     if device:
#     #         # If the device exists but is not unselected, raise an error
#     #         if device.status != 'unselected':
#     #             raise serializers.ValidationError("Device with this IMEI is already in use.")
#     #         data['device'] = device

#     #     return data
#     def validate(self, data):
#         # Check if the user exists or not
#         user = UserCustomModel.objects.filter(email=data['email']).first()
#         if not user:
#             user = UserCustomModel.objects.create_user(
#                 first_name=data['first_name'],
#                 last_name=data['last_name'],
#                 email=data['email'],
#                 password=data['password']
#             )
#         data['user'] = user

#         # If the user is a department user or finance manager, find their parent
#         if user.role in ['department_user', 'finance_manager']:
#             # Find the parent of the user from UserCreationLog
#             parent = UserCreationLog.objects.filter(created_user=user).first()
#             if not parent:
#                 raise serializers.ValidationError("No parent user found for this user.")

#             # Check the devices in the parent's inventory (via batch assigned to the dealer)
#             # Assuming 'parent.creator' is the dealer and we check batches assigned to the dealer
#             dealer_batches = DeviceBatchAssignment.objects.filter(assigned_to=parent.creator)

#             # Check if the provided device is in the inventory of the batches assigned to the parent
#             device = DeviceInventory.objects.filter(imei=data['ident'], batch__in=dealer_batches).first()

#             if not device:
#                 raise serializers.ValidationError(f"Device with IMEI {data['ident']} is not available in the assigned dealer's inventory.")
            
#             # Ensure the device has not been selected or assigned already
#             if device.status != 'unselected':
#                 raise serializers.ValidationError(f"Device with IMEI {data['ident']} is already in use.")
            
#             data['device'] = device

#         # Existing vehicle validation logic
#         vehicle = Car.objects.filter(vinNumber=data['vin']).first()
#         if vehicle:
#             data['vehicle'] = vehicle

#         return data

#     # @transaction.atomic
#     def create(self, validated_data):
#         user = validated_data['user']

#         # Check if a vehicle exists
#         vehicle = validated_data.get('vehicle')
#         if not vehicle:
#             # Use CarSerializer to create the car
#             car_data = {
#                 'vinNumber': validated_data['vin'],
#                 'model': validated_data['model'],
#                 'year': validated_data['year'],
#                 'make': validated_data['make'],
#                 'price': validated_data.get('vehicle_price'),
                
#                 'user': user
#             }
#             car_serializer = CarSerializer(data=car_data)
#             car_serializer.is_valid(raise_exception=True)
#             vehicle = car_serializer.save()  # Save the car instance to the database
#         else:
#             # Update the existing vehicle
#             vehicle.vinNumber = validated_data['vin']
#             vehicle.model = validated_data['model']
#             vehicle.year = validated_data['year']
#             vehicle.make = validated_data['make']
#             vehicle.price = validated_data.get('vehicle_price')
#             vehicle.save()

#         # Ensure the vehicle is saved
#         if not vehicle.pk:
#             vehicle.save()

#         # Check if a device exists
#         device = validated_data.get('device')
#         if not device:
#             # Use DeviceSerializer to create the device
#             device_data = {
#                 'ident': validated_data['ident'],
#                 'name': validated_data['ident'],
#                 'status': 'unselected',
#                 'device_type_id': validated_data.get('device_type_id'),
#                 'device_id': validated_data.get('device_id'),
#                 'price': validated_data.get('device_price')
#                 # 'serial_number': validated_data.get('serial_number')
#             }
#             device_serializer = DeviceSerializer(data=device_data)
#             device_serializer.is_valid(raise_exception=True)
#             device = device_serializer.save()  # Save the device using the DeviceSerializer
#         else:
#             # Update the existing device
#             device.ident = validated_data['ident']
#             device.name = validated_data['ident']
#             device.status = 'selected'
#             device.device_type_id = validated_data.get('device_type_id')
#             device.price = validated_data.get('device_price')
#             device.save()

#         # Ensure the device is saved
#         if not device.pk:
#             raise ValueError("Device instance must be saved before proceeding.")

#         return {
#             "user": user,
#             "vehicle": vehicle,
#             "device": device
#         }
