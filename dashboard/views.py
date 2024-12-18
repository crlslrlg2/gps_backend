from rest_framework.views import APIView
import pandas as pd
from backend.Permissions import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import *
from rest_framework_simplejwt.tokens import RefreshToken
from auth_app.models import UserCustomModel
from rest_framework.permissions import AllowAny,IsAuthenticated
import json
import requests
from .models import *
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
import uuid
from django.shortcuts import get_object_or_404
import traceback
from backend.utils import *
from auth_app.models import *
from devices.models import *
from devices.serializer import *
from django.db.models import Q
from django.core.cache import cache  # Optional, if you want to cache device types
# Admin-only view
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class SignUpView(APIView):
    # permission_classes = [IsAuthenticated, IsDepartmentUser]
    permission_classes = [AllowAny] 
    def post(self, request):
         
       
        password = request.data.get('password', None)
        role = request.data.get('role')

        # if not role:
        #     return Response({
        #         'error': 'Invalid role',
        #         'status': 400
        #     }, status=status.HTTP_400_BAD_REQUEST)

        # if request.user.role in ['agency', 'finance_manager', 'department_user']:
        #     if request.data.get('role') != 'user':
        #         return Response({
        #             'error': f'You are not authorized to create {role} account',
        #             'status': 403
        #         }, status=status.HTTP_403_FORBIDDEN)

        # if request.user.role == 'dealer_super_admin':
        #     if request.data.get('role') == 'agency' or request.data.get('role') == 'safelink' or request.data.get('role') == 'dealer_super_admin':
        #         return Response({
        #             'error': f'You are not authorized to create {role} account',
        #             'status': 403
        #         }, status=status.HTTP_403_FORBIDDEN)

        if password is None:
            return Response({
                'error': 'Password is required',
                'status': 400
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Log the creation of the new user
            # UserCreationLog.objects.create(
            #     creator=request.user,  # The user who is making the request
            #     created_user=serializer.instance  # The newly created user
            # )

            return Response({
                "user": serializer.data,
                "tokens": get_tokens_for_user(serializer.instance),
                "status": "201"
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'error': str(e),
                'status': 400
            }, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]


    def post(self, request):
        email = str(request.data.get('email')).lower()
        user = UserCustomModel.objects.exclude(role='user').filter(email=email).first()
        # user = UserCustomModel.objects.filter(email=email).first() 
        if user is None:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_404_NOT_FOUND)


        password = request.data.get('password', None)
      
        token = request.data.get('token',None)
        # print(token)
        # Validate the email and password

       
      
        # if user.accountType in ['google', 'facebook']:
        #     if token is None:
        #         return Response({"error": "Token is required", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        # Validate the social token
        

        user = UserCustomModel.objects.filter(email=email).first()
        if user is None:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_404_NOT_FOUND)


        if user.accountType == 'default' or password is not None:
            if not user.check_password(password):
                return Response({"error": "Invalid Credentials"}, status=status.HTTP_404_NOT_FOUND)


        return Response({
            "user": UserSerializer(user).data,
            "tokens": get_tokens_for_user(user),
            "status": "200"
        }, status=status.HTTP_200_OK)

class DeviceBatchUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, IsSafelink]

    REQUIRED_COLUMNS = [
        'IMEI', 'Sim Card # (ICCID)', 'Sim Provider',
        'Shipment Date','Model','Serial #'
    ]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        data['created_by'] = request.user.id

        if not data.get('batch_number'):
            data['batch_number'] = self.generate_unique_batch_number()

        serializer = DeviceBatchUploadSerializer(data=data)

        if serializer.is_valid():
            batch_instance = serializer.save()
            uploaded_file = batch_instance.uploaded_file

            if uploaded_file:
                try:
                    if not uploaded_file.name.endswith('.xlsx'):
                        return Response({
                            'success': False,
                            'data': {"detail": "Uploaded file must be an Excel (.xlsx) file."},
                            'status': status.HTTP_400_BAD_REQUEST
                        }, status=status.HTTP_400_BAD_REQUEST)

                    excel_data = pd.read_excel(uploaded_file, engine='openpyxl')

                    missing_columns = [column for column in self.REQUIRED_COLUMNS if column not in excel_data.columns]
                    if missing_columns:
                        return Response({
                            'success': False,
                            'data': {"detail": f"File is missing required columns: {', '.join(missing_columns)}"},
                            'status': status.HTTP_400_BAD_REQUEST
                        }, status=status.HTTP_400_BAD_REQUEST)

                    for index, row in excel_data.iterrows():
                        device_inventory = DeviceInventory(
                            imei=row.get('IMEI'),
                            sim_card=row.get('Sim Card # (ICCID)'),
                            iccid=row.get('Sim Provider'),
                            # received_date=row.get('Received Date'),
                            shipped_date=row.get('Shipment Date'),
                            serial_number=row.get('Serial #'),
                            model=row.get('Model'),
                            batch=batch_instance,
                            status='notmonitor'
                        )
                        device_inventory.save()

                    return Response({
                        'success': True,
                        'data': serializer.data,
                        'status': status.HTTP_201_CREATED
                    }, status=status.HTTP_201_CREATED)

                except pd.errors.EmptyDataError:
                    return Response({
                        'success': False,
                        'data': {"detail": "Uploaded file is empty."},
                        'status': status.HTTP_400_BAD_REQUEST
                    }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({
                        'success': False,
                        'data': {"detail": f"Error processing the file: {str(e)}"},
                        'status': status.HTTP_400_BAD_REQUEST
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'data': {"detail": "No file uploaded."},
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': False,
                'data': serializer.errors,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

    def generate_unique_batch_number(self):
        while True:
            batch_number = str(uuid.uuid4())[:8]
            if not DeviceBatchUpload.objects.filter(batch_number=batch_number).exists():
                return batch_number

class DevicesInBatchDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSafelink]

    def get(self, request, batch_id, *args, **kwargs):
        batch = DeviceInventory.objects.filter(batch_id=batch_id)
        serializer = DeviceInventorySerializer(batch, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'status': status.HTTP_200_OK
        })

    def post(self, request, batch_id, *args, **kwargs):
        data = request.data.copy()
        data['batch'] = batch_id
        serializer = DeviceInventorySerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'status': status.HTTP_201_CREATED
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'data': serializer.errors,
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, batch_id, *args, **kwargs):
        batch = get_object_or_404(DeviceInventory, batch_id=batch_id, id=request.data.get('deviceId'))
        serializer = DeviceInventorySerializer(batch, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'status': status.HTTP_200_OK
            })
        return Response({
            'success': False,
            'data': serializer.errors,
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, batch_id, *args, **kwargs):
        device_id = request.data.get('deviceId')

        if not device_id or not batch_id:
            return Response({
                'success': False,
                'data': {"detail": "Both device_id and batch_id are required."},
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = DeviceInventory.objects.filter(id=device_id, batch_id=batch_id).first()
            if not device:
                return Response({
                    'success': False,
                    'data': {"detail": "Device not found in the specified batch."},
                    'status': status.HTTP_404_NOT_FOUND
                }, status=status.HTTP_404_NOT_FOUND)
            device.delete()
            return Response({
                'success': True,
                'data': {"detail": "Device deleted successfully."},
                'status': status.HTTP_204_NO_CONTENT
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                'success': False,
                'data': {"detail": str(e)},
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

class BatchListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        status_filter = request.query_params.get("type")
        role = request.user.role

        # Check for valid status filter
        if status_filter not in ['all', 'assigned', 'unassigned']:
            return Response({
                'success': False,
                'data': {"detail": "Invalid status filter"},
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        # For safelink role: no restrictions, can view all batches
        if role == 'safelink':
            if status_filter == 'all':
                batches = DeviceBatchUpload.objects.all()
            else:
                batches = DeviceBatchUpload.objects.filter(status=status_filter)

        # For finance_manager: view batches created by their parent dealer
        elif role == 'finance_manager':
            # Find the parent dealer (creator) of the current finance manager
            parent_log = UserCreationLog.objects.filter(created_user=request.user).first()
            if not parent_log:
                return Response({
                    'success': False,
                    'data': {"detail": "Parent dealer not found for this finance manager."},
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)

            # Parent dealer is the creator
            parent_dealer = parent_log.creator

            # Get batches where parent dealer is assigned_to or assigned_by
            if status_filter == 'all':
                batches_ids = DeviceBatchAssignment.objects.filter(
                    Q(assigned_to=parent_dealer) | Q(assigned_by=parent_dealer)
                ).values_list('batch_id', flat=True)
            else:
                batches_ids = DeviceBatchAssignment.objects.filter(
                    Q(assigned_to=parent_dealer) | Q(assigned_by=parent_dealer),
                    batch__status=status_filter
                ).values_list('batch_id', flat=True)

            batches = DeviceBatchUpload.objects.filter(id__in=batches_ids)

        # For other roles: view their own assigned or created batches
        else:
            if status_filter == 'all':
                # Get batches where assigned_to or assigned_by is the current user
                batches_ids = DeviceBatchAssignment.objects.filter(
                    Q(assigned_to=request.user) | Q(assigned_by=request.user)
                ).values_list('batch_id', flat=True)
            else:
                batches_ids = DeviceBatchAssignment.objects.filter(
                    Q(assigned_to=request.user) | Q(assigned_by=request.user),
                    batch__status=status_filter
                ).values_list('batch_id', flat=True)

            # Filter DeviceBatchUpload by the batch IDs retrieved above
            batches = DeviceBatchUpload.objects.filter(id__in=batches_ids)

        # Serialize and return the data
        serializer = DeviceBatchUploadSerializer(batches, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


    def delete(self, request,batch_id):
        
        # print(request.data.get("type"))
        batches = DeviceBatchUpload.objects.filter(id=batch_id).first()
        if not batches:
            return Response({"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        delete_s3_object(bucket_name=settings.AWS_STORAGE_BUCKET_NAME,object_key=batches.uploaded_file)
        batches.delete()
        print("batch_id: ", batch_id)
        return Response({"detail": "Batch deleted successfully.","status":204}, status=status.HTTP_204_NO_CONTENT)

class UserView(APIView):
    permission_classes = [IsAuthenticated, IsSafelink]
    ROLE_CHOICES = [
        'safelink',
        'agency',
        'dealer_super_admin',
        'dealer_admin',
        'finance_manager',
        'department_user',  
        'user' ,
        'all'
    ]
    
    def get(self, request):
        userRole=request.query_params.get("role")
        if userRole not in self.ROLE_CHOICES:
            return Response({
                'success': False,
                'data': {"detail": "Invalid user role"},
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        if userRole == 'all':
            users = UserCustomModel.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })
        users = UserCustomModel.objects.filter(role=userRole)
        serializer = UserSerializer(users, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })



class DevicesListView(APIView):
    
    def get(self, request):
        device_status = request.query_params.get('status', None)  
        user_id = request.data.get('user', None)  
        
        if user_id:
            UserDevices = UserSelectedDeviceSerializer(UserSelectedDevice.objects.filter(user=user_id), many=True)
            return Response({"data": UserDevices.data, "status": 200}, status=status.HTTP_200_OK)
        if str(device_status).strip() == "all":
            devices = Device.objects.all()
            serializer = DeviceSerializer(devices, many=True)
            print(request.user)
            return Response({"data": serializer.data, "status": 200}, status=status.HTTP_200_OK)
        UserDevices = UserSelectedDeviceSerializer(UserSelectedDevice.objects.filter(user=request.user), many=True)
        return Response({"data": UserDevices.data, "status": 200}, status=status.HTTP_200_OK)
    





# class BatchAssignmentView(APIView):
#     permission_classes = [IsAuthenticated, IsDealerSuperAdmin]

#     def post(self, request):
#         user_id = request.data.get('user')
#         batch_id = request.data.get('batch')

#         # Validate that both user and batch are provided
#         if not user_id or not batch_id:
#             return Response({"detail": "Both user and batch are required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Fetch the user to whom the batch will be assigned
#             assigned_to = get_object_or_404(UserCustomModel, id=user_id, role__in=['agency', 'dealer_super_admin','dealer_admin'])

#             # Fetch the batch to be assigned
#             batch = get_object_or_404(DeviceBatchUpload, id=batch_id)

#             # Optionally, check if the batch has a previous assignment and fetch it
#             previous_assignment = DeviceBatchAssignment.objects.filter(batch=batch).last()

#             # Create the new batch assignment
#             DeviceBatchAssignment.objects.create(
#                 batch=batch,
#                 assigned_by=request.user,  # The user making the assignment
#                 assigned_to=assigned_to,
#                 previous_assignment=previous_assignment.assigned_to if previous_assignment else None
#             )

#             # Update the batch status to "assigned"
#             batch.status = 'assigned'
#             batch.save()

#             # Update the status of all devices in the batch to "monitor"
#             DeviceInventory.objects.filter(batch=batch).update(status='monitor')

#             return Response({
#                 "detail": f"Batch {batch.batch_number} successfully assigned to {assigned_to.email}, and device statuses updated to 'monitor'.",
#                 "status": status.HTTP_201_CREATED
#             }, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             # Handle any exceptions and provide an appropriate error message
#             return Response({
#                 "detail": f"Error occurred: {str(e)}",
#                 "status": status.HTTP_400_BAD_REQUEST
#             }, status=status.HTTP_400_BAD_REQUEST)
            

class BatchAssignmentView(APIView):
    permission_classes = [IsAuthenticated, IsDealerSuperAdmin]

    def post(self, request):
        user_id = request.data.get('user')
        batch_id = request.data.get('batch')

        # Validate that both user and batch are provided
        if not user_id or not batch_id:
            return Response({"detail": "Both user and batch are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the user to whom the batch will be assigned
            assigned_to = get_object_or_404(UserCustomModel, id=user_id, role__in=['agency', 'dealer_super_admin', 'dealer_admin'])

            # Fetch the batch to be assigned
            batch = get_object_or_404(DeviceBatchUpload, id=batch_id)

            # Optionally, check if the batch has a previous assignment and fetch it
            previous_assignment = DeviceBatchAssignment.objects.filter(batch=batch).last()

            # Create the new batch assignment
            DeviceBatchAssignment.objects.create(
                batch=batch,
                assigned_by=request.user,  # The user making the assignment
                assigned_to=assigned_to,
                previous_assignment=previous_assignment.assigned_to if previous_assignment else None
            )

            # Update the batch status to "assigned"
            batch.status = 'assigned'
            batch.save()

            # Update the status of all devices in the batch to "monitor"
            DeviceInventory.objects.filter(batch=batch).update(status='monitor')

            # If assigned_to is not an agency, upload devices to Flespi in bulk and insert into the Device table
            if assigned_to.role != 'agency':
                devices_in_batch = DeviceInventory.objects.filter(batch=batch)

                # Fetch device types from Flespi (cache them if needed)
                device_types = self.get_flespi_device_types()

                # Prepare the bulk device creation payload for Flespi
                bulk_device_data = []
                print("devices_in_batch",devices_in_batch) 
                for device_inventory in devices_in_batch:
                    # Find the device type by matching some criteria (for example, based on `imei` or a model)
                    device_type_id = self.get_device_type_id(device_inventory, device_types)
                    # print("device_type_id",device_type_id)
                    if device_type_id is None:
                        continue
                        # return Response({"detail": f"Device type not found for {device_inventory.imei}"},
                                        # status=status.HTTP_400_BAD_REQUEST)
                    # print("device_inventory.imei",device_inventory.imei)
                    # Prepare the device data to be sent to Flespi
                    device_data = {
                        "name": device_inventory.serial_number,  # Use Serial Number as the device name
                        "device_type_id": device_type_id,  # Adjust as per your logic to find the correct device type ID
                        "configuration": {
                            "ident": device_inventory.imei,  # Only Serial Number is used as ident
                            "settings_polling": "once"  # Ensure the configuration is valid
                        }
                    }
                    print("device_data",device_data)
                    bulk_device_data.append(device_data)
                print("device_data",bulk_device_data)
                # Send the bulk creation request to Flespi
                response = requests.post(
                    "https://flespi.io/gw/devices",
                    headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"},
                    json=bulk_device_data
                )

                response_data = response.json()
                print("response_data",response_data) 
                # Check if the response contains errors
                if "errors" in response_data:
                    errors = response_data["errors"]
                    return Response({
                        "detail": f"Flespi bulk upload failed: {errors[0].get('reason')}",
                        "status": status.HTTP_400_BAD_REQUEST
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Process the successful Flespi response
                successfully_uploaded_devices = response_data.get("result", [])
                # not for production devices
                for device_result in successfully_uploaded_devices:
                    # Create corresponding entries in the Device table
                    Device.objects.create(
                        name=device_result['name'],
                        device_id=device_result['id'],
                        device_type_id=device_result['device_type_id'],
                        ident=device_result['configuration']['ident'],
                        status='unselected',
                        price=0  # You can modify this as per your logic
                    )

            return Response({
                "detail": f"Batch {batch.batch_number} successfully assigned to {assigned_to.email}, devices uploaded to Flespi, and statuses updated.",
                "status": status.HTTP_201_CREATED
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Handle any exceptions and provide an appropriate error message
            return Response({
                "detail": f"Error occurred: {str(e)}",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_flespi_device_types(self):
        """
        Fetches the device types from Flespi and caches them.
        """
        # Check cache first
        device_types = cache.get('flespi_device_types')
        if not device_types:
            try:
                device_types_response = requests.get(
                    "https://flespi.io/gw/channel-protocols/all/device-types/all?fields=name,id,title",
                    headers={"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
                )
                device_types_response.raise_for_status()
                device_types = device_types_response.json().get('result', [])
                # Cache the device types for future use (optional)
                cache.set('flespi_device_types', device_types, timeout=86400)  # Cache for 24 hours
            except requests.exceptions.RequestException:
                raise ValueError("Failed to fetch device types from Flespi.")
        return device_types

    def get_device_type_id(self, device_inventory, device_types):
        """
        Matches a device in DeviceInventory with a device type from Flespi.
        This can be based on the model name or any other criteria.
        """
        print("device_types",device_inventory)
        # Example: match based on the model name in DeviceInventory and the device type from Flespi
        for device_type in device_types:
            # print(device_inventory.model.lower() , device_type['name'].lower())
            # Check if the device model contains the name of the device type
            if  device_inventory.model.lower() in device_type['name'].lower():
                return device_type['id']
        return None
            
class VehicleAndDeviceCreateAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = VehicleAndDeviceCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                "seller": {
                    "first_name": result['seller'].first_name,
                    "last_name": result['seller'].last_name,
                    "email": result['seller'].email
                },
                "buyer": {
                    "first_name": result['buyer'].first_name,
                    "last_name": result['buyer'].last_name,
                    "email": result['buyer'].email
                },
                "vehicle": {
                    "vin": result['vehicle'].vinNumber,
                    "model": result['vehicle'].model,
                    "year": result['vehicle'].year,
                    "make": result['vehicle'].make
                },
                "device": {
                    "imei": result['device'].ident
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
# class VehicleAndDeviceCreateAPIView(APIView):

#     def post(self, request, *args, **kwargs):
#         try:
#             serializer = VehicleAndDeviceCreateSerializer(data=request.data)
#             if serializer.is_valid():
#                 result = serializer.save()

#                 # Ensure that both vehicle and device have been saved
#                 vehicle = result['vehicle']
#                 device = result['device']

#                 # Ensure the vehicle and device are saved before calling get_or_create
#                 if not vehicle.pk:
#                     raise ValueError("Vehicle instance must be saved before proceeding.")
#                 if not device.pk:
#                     raise ValueError("Device instance must be saved before proceeding.")

#                 # Use 'device_id' instead of 'device'
#                 UserCarsWithDevice.objects.get_or_create(car=vehicle, device=device)
#                 UserSelectedDevice.objects.get_or_create(user=result['user'], device_id=device)
#                 device.status="selected"
#                 device.save()
#                 return Response({
#                     "user": {
#                         "first_name": result['user'].first_name,
#                         "last_name": result['user'].last_name,
#                         "email": result['user'].email
#                     },
#                     "vehicle": {
#                         "vin": result['vehicle'].vinNumber,
#                         "model": result['vehicle'].model,
#                         "year": result['vehicle'].year,
#                         "make": result['vehicle'].make
#                     },
#                     "device": {
#                         "imei": result['device'].ident
#                     }
#                 }, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             return Response({
#                 "detail": f"An error occurred: {str(e)}"
#             }, status=status.HTTP_400_BAD_REQUEST)

            